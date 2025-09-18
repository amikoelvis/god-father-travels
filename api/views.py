from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
import uuid

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

# -------------------------------
# 1. Users
# -------------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # Admin only

# -------------------------------
# 2. Vehicles & Availability
# -------------------------------
class VehicleCategoryViewSet(viewsets.ModelViewSet):
    queryset = VehicleCategory.objects.all()
    serializer_class = VehicleCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all().select_related('category').prefetch_related('availabilities')
    serializer_class = VehicleSerializer
    filterset_class = VehicleFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['daily_rate', 'seats', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    permission_classes = [IsAdminOrReadOnly]

class VehicleAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = VehicleAvailability.objects.all()
    serializer_class = VehicleAvailabilitySerializer
    permission_classes = [IsAdminOrReadOnly]

# -------------------------------
# 3. Safari Packages
# -------------------------------
class SafariPackageViewSet(viewsets.ModelViewSet):
    queryset = SafariPackage.objects.all().prefetch_related('itinerary')
    serializer_class = SafariPackageSerializer
    filterset_class = SafariFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['base_price', 'duration_days', 'seats_available']
    search_fields = ['name', 'description', 'region']
    permission_classes = [IsAdminOrReadOnly]

class SafariItineraryViewSet(viewsets.ModelViewSet):
    queryset = SafariItinerary.objects.all()
    serializer_class = SafariItinerarySerializer
    permission_classes = [IsAdminOrReadOnly]

# -------------------------------
# 4. Bookings
# -------------------------------
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by("-created_at")
    permission_classes = [IsCustomerOrAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# -------------------------------
# 5. Payments & Invoices
# -------------------------------
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by("-created_at")
    serializer_class = PaymentSerializer
    permission_classes = [IsCustomerOrAdmin]

    @action(detail=False, methods=["post"], url_path="start")
    def start(self, request):
        """
        Start payment for a booking.
        Expects JSON: { "booking_id": "<uuid>", "provider": "flutterwave" }
        """
        booking_id = request.data.get("booking_id")
        provider = request.data.get("provider", "mock")

        try:
            booking = Booking.objects.get(pk=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        # Prevent duplicate payments
        if hasattr(booking, "payment"):
            return Response({"detail": "Payment already exists for this booking"}, status=status.HTTP_400_BAD_REQUEST)

        tx_ref = str(uuid.uuid4())
        payment = Payment.objects.create(
            booking=booking,
            provider=provider,
            amount=booking.total_price,
            currency="UGX",
            status="pending",
            transaction_ref=tx_ref,
        )

        # Mock payment link
        payment_link = f"https://payment-gateway.example/pay/{tx_ref}"

        return Response({
            "payment_link": payment_link,
            "transaction_ref": tx_ref,
            "status": "pending",
        }, status=status.HTTP_201_CREATED)

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by("-issued_at")
    serializer_class = InvoiceSerializer
    permission_classes = [IsCustomerOrAdmin]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["payment__transaction_ref"]
    ordering_fields = ["issued_at"]

# -------------------------------
# 6. Reviews
# -------------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by("-created_at")
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomerOrAdmin]

# -------------------------------
# 7. Notifications
# -------------------------------
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

# -------------------------------
# 8. Admin Logs
# -------------------------------
class AdminLogViewSet(viewsets.ModelViewSet):
    queryset = AdminLog.objects.all().order_by("-created_at")
    serializer_class = AdminLogSerializer
    permission_classes = [permissions.IsAdminUser]

# -------------------------------
# 9. Payment Webhook
# -------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def payment_webhook(request):
    """
    Generic webhook handler.
    Expects JSON: { "transaction_ref": "...", "status": "success" }
    """
    data = request.data
    tx_ref = data.get("transaction_ref") or data.get("tx_ref")
    status_str = data.get("status")

    if not tx_ref:
        return Response({"detail": "missing transaction_ref"}, status=400)

    # TODO: verify provider signature in production

    try:
        payment = Payment.objects.select_for_update().get(transaction_ref=tx_ref)
    except Payment.DoesNotExist:
        return Response({"detail": "payment not found"}, status=404)

    if payment.status == "success":
        return Response({"detail": "already processed"}, status=200)

    if status_str and status_str.lower() in ("success", "completed", "paid"):
        payment.status = "success"
        payment.save()
        booking = payment.booking
        booking.status = "confirmed"
        booking.save()
        return Response({"detail": "payment confirmed"}, status=200)
    else:
        payment.status = "failed"
        payment.save()
        return Response({"detail": "payment failed"}, status=200)
