from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

import uuid, hashlib, hmac, base64
from urllib.parse import urlencode
import boto3
from datetime import timedelta

from .tasks import send_booking_email, generate_invoice_and_email
from .models import (
    User, VehicleCategory, Vehicle, VehicleAvailability,
    SafariPackage, SafariItinerary,
    Booking, Payment, Invoice,
    Review, Notification, AdminLog
)
from .serializers import (
    UserSerializer, VehicleCategorySerializer, VehicleSerializer, VehicleAvailabilitySerializer,
    SafariPackageSerializer, SafariItinerarySerializer,
    BookingSerializer, BookingCreateSerializer,
    PaymentSerializer, InvoiceSerializer,
    ReviewSerializer, NotificationSerializer, AdminLogSerializer
)
from .filters import VehicleFilter, SafariFilter
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrAdmin, IsCustomerOrAdmin


CACHE_TIMEOUT = 60 * 10  # 10 minutes


# -------------------------------
# 1. Users
# -------------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# -------------------------------
# 2. Vehicles & Availability
# -------------------------------
class VehicleCategoryViewSet(viewsets.ModelViewSet):
    queryset = VehicleCategory.objects.all()
    serializer_class = VehicleCategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all().select_related(
        "category"
    ).prefetch_related("availabilities", "images")
    serializer_class = VehicleSerializer
    filterset_class = VehicleFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["daily_rate", "seats", "created_at"]
    search_fields = ["name", "description", "category__name"]
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=False, methods=["get"], url_path="popular", permission_classes=[AllowAny])
    def popular(self, request):
        cache_key = "popular_vehicles"
        vehicles = cache.get(cache_key)
        if vehicles is None:
            vehicles = list(
                Vehicle.objects.filter(is_popular=True)
                .select_related("category")
                .prefetch_related("images")[:10]
            )
            cache.set(cache_key, vehicles, CACHE_TIMEOUT)
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)


class VehicleAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = VehicleAvailability.objects.all().select_related("vehicle")
    serializer_class = VehicleAvailabilitySerializer
    permission_classes = [IsAdminOrReadOnly]


# -------------------------------
# 3. Safari Packages
# -------------------------------
class SafariPackageViewSet(viewsets.ModelViewSet):
    queryset = SafariPackage.objects.all().prefetch_related("itinerary", "images")
    serializer_class = SafariPackageSerializer
    filterset_class = SafariFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["base_price", "duration_days", "seats_available"]
    search_fields = ["name", "description", "region"]
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=False, methods=["get"], url_path="featured", permission_classes=[AllowAny])
    def featured(self, request):
        cache_key = "featured_safaris"
        safaris = cache.get(cache_key)
        if safaris is None:
            safaris = list(
                SafariPackage.objects.filter(is_featured=True)
                .prefetch_related("itinerary", "images")[:10]
            )
            cache.set(cache_key, safaris, CACHE_TIMEOUT)
        serializer = self.get_serializer(safaris, many=True)
        return Response(serializer.data)


class SafariItineraryViewSet(viewsets.ModelViewSet):
    queryset = SafariItinerary.objects.all().select_related("safari_package")
    serializer_class = SafariItinerarySerializer
    permission_classes = [IsAdminOrReadOnly]


# -------------------------------
# 4. Bookings
# -------------------------------
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().select_related(
        "user", "safari_package", "vehicle"
    ).order_by("-created_at")
    permission_classes = [IsCustomerOrAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        send_booking_email.delay(str(booking.id))


# -------------------------------
# 5. Payments & Invoices (Pesapal)
# -------------------------------
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related("booking").order_by("-created_at")
    serializer_class = PaymentSerializer
    permission_classes = [IsCustomerOrAdmin]

    @action(detail=False, methods=["post"], url_path="start")
    def start(self, request):
        booking_id = request.data.get("booking_id")
        try:
            booking = Booking.objects.select_related("user").get(pk=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(booking, "payment"):
            return Response({"detail": "Payment already exists"}, status=status.HTTP_400_BAD_REQUEST)

        tx_ref = str(uuid.uuid4())
        payment = Payment.objects.create(
            booking=booking,
            provider="pesapal",
            amount=booking.total_price,
            currency="UGX",
            status="pending",
            transaction_ref=tx_ref,
        )

        data = {
            "amount": booking.total_price,
            "description": f"Booking {booking.id}",
            "type": "MERCHANT",
            "reference": tx_ref,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "callback_url": settings.PESAPAL_CALLBACK_URL,
        }

        encoded_data = urlencode(data)
        signature = base64.b64encode(
            hmac.new(
                settings.PESAPAL_CONSUMER_SECRET.encode(),
                encoded_data.encode(),
                hashlib.sha1
            ).digest()
        ).decode()

        payment_link = f"{settings.PESAPAL_API_BASE}/postPesapalDirectOrderV4?{encoded_data}&signature={signature}&consumer_key={settings.PESAPAL_CONSUMER_KEY}"

        return Response({
            "payment_link": payment_link,
            "transaction_ref": tx_ref,
            "status": payment.status,
        }, status=status.HTTP_201_CREATED)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().select_related("payment").order_by("-issued_at")
    serializer_class = InvoiceSerializer
    permission_classes = [IsCustomerOrAdmin]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["payment__transaction_ref"]
    ordering_fields = ["issued_at"]


# -------------------------------
# 6. Reviews
# -------------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related("user", "safari_package", "vehicle").order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomerOrAdmin]


# -------------------------------
# 7. Notifications
# -------------------------------
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().select_related("user").order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# -------------------------------
# 8. Admin Logs
# -------------------------------
class AdminLogViewSet(viewsets.ModelViewSet):
    queryset = AdminLog.objects.all().select_related("user").order_by("-created_at")
    serializer_class = AdminLogSerializer
    permission_classes = [permissions.IsAdminUser]


# -------------------------------
# 9. Pesapal Webhook
# -------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def pesapal_webhook(request):
    data = request.data or request.query_params
    tx_ref = data.get("reference")
    status_str = data.get("status")

    if not tx_ref:
        return Response({"detail": "missing transaction reference"}, status=400)

    try:
        payment = Payment.objects.select_for_update().select_related("booking").get(transaction_ref=tx_ref)
    except Payment.DoesNotExist:
        return Response({"detail": "payment not found"}, status=404)

    if payment.status == "success":
        return Response({"detail": "already processed"}, status=200)

    if status_str and status_str.upper() == "COMPLETED":
        payment.status = "success"
        payment.save()
        booking = payment.booking
        booking.status = "confirmed"
        booking.save()
        generate_invoice_and_email.delay(str(payment.id))
        send_booking_email.delay(str(booking.id))
        return Response({"detail": "Pesapal payment confirmed"}, status=200)
    else:
        payment.status = "failed"
        payment.save()
        return Response({"detail": "Pesapal payment failed"}, status=200)


# -------------------------------
# 10. Presigned S3 Upload
# -------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_presigned_url(request):
    file_name = request.data.get("file_name")
    file_type = request.data.get("file_type")

    if not file_name or not file_type:
        return Response({"error": "file_name and file_type are required"}, status=400)

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    key = f"uploads/{uuid.uuid4()}_{file_name}"

    presigned_post = s3_client.generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Fields={"Content-Type": file_type},
        Conditions=[{"Content-Type": file_type}],
        ExpiresIn=3600
    )

    return Response({
        "url": presigned_post["url"],
        "fields": presigned_post["fields"],
        "key": key
    })
