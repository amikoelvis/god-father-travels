from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import (
    User,
    VehicleCategory, Vehicle, VehicleAvailability,
    SafariPackage, SafariItinerary,
    Booking, Payment, Invoice,
    Review, Notification, AdminLog
)

# -------------------------------
# 1. User Serializer
# -------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone", "role",
            "is_verified", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 2. Vehicle Serializers
# -------------------------------
class VehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleCategory
        fields = ["id", "name", "description"]


class VehicleAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleAvailability
        fields = ["id", "date", "is_booked"]


class VehicleSerializer(serializers.ModelSerializer):
    category = VehicleCategorySerializer(read_only=True)
    availabilities = VehicleAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id", "category", "name", "description", "seats",
            "daily_rate", "with_driver", "image",
            "is_available", "created_at", "availabilities"
        ]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 3. Safari Package Serializers
# -------------------------------
class SafariItinerarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SafariItinerary
        fields = ["id", "day_number", "title", "description"]


class SafariPackageSerializer(serializers.ModelSerializer):
    itinerary = SafariItinerarySerializer(many=True, read_only=True)

    class Meta:
        model = SafariPackage
        fields = [
            "id", "name", "description", "region", "duration_days",
            "base_price", "seats_available", "image",
            "created_at", "itinerary"
        ]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 4. Booking Serializer
# -------------------------------
class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    safari = SafariPackageSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "user", "booking_type", "vehicle", "safari",
            "start_date", "end_date", "total_price",
            "status", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 5. Payment & Invoice Serializers
# -------------------------------
class PaymentSerializer(serializers.ModelSerializer):
    idempotency_key = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional unique key to prevent duplicate payments"
    )

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["status", "created_at"]

    def validate_provider(self, value):
        allowed = ["pesapal"]
        if value.lower() not in allowed:
            raise serializers.ValidationError(f"Only {allowed} is supported")
        return value

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["issued_at"]

# -------------------------------
# 6. Reviews
# -------------------------------
class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "user", "safari", "vehicle",
            "rating", "comment", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 7. Notifications
# -------------------------------
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "user", "message", "is_read", "created_at"]
        read_only_fields = ["id", "created_at"]


# -------------------------------
# 8. Admin Logs
# -------------------------------
class AdminLogSerializer(serializers.ModelSerializer):
    admin = UserSerializer(read_only=True)

    class Meta:
        model = AdminLog
        fields = ["id", "admin", "action", "details", "created_at"]
        read_only_fields = ["id", "created_at"]

class BookingCreateSerializer(serializers.ModelSerializer):
    idempotency_key = serializers.CharField(write_only=True, required=False, allow_null=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "user", "booking_type", "vehicle", "safari",
            "start_date", "end_date", "pax", "total_price",
            "status", "idempotency_key", "details", "created_at"
        ]
        read_only_fields = ["id", "status", "created_at", "details"]

    def validate(self, attrs):
        btype = attrs.get("booking_type")
        if btype == "vehicle" and not attrs.get("vehicle"):
            raise serializers.ValidationError("Vehicle booking requires a vehicle.")
        if btype == "safari" and not attrs.get("safari"):
            raise serializers.ValidationError("Safari booking requires a safari.")
        # date checks
        if attrs.get("end_date") and attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError("end_date must be after start_date")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        idempotency_key = validated_data.pop("idempotency_key", None)

        # If idempotency_key provided and a booking exists for this user with same key, return it
        if idempotency_key:
            existing = Booking.objects.filter(user=user, idempotency_key=idempotency_key).first()
            if existing:
                return existing

        # start atomic transaction and row locking
        with transaction.atomic():
            btype = validated_data.get("booking_type")
            if btype == "vehicle":
                vehicle = Vehicle.objects.select_for_update().get(pk=validated_data["vehicle"].pk)
                # check for conflicts using VehicleAvailability
                start = validated_data["start_date"]
                end = validated_data.get("end_date", start)
                conflict = VehicleAvailability.objects.filter(
                    vehicle=vehicle,
                    date__range=(start, end),
                    is_booked=True
                ).exists()
                if conflict:
                    raise serializers.ValidationError("Selected vehicle is not available for the requested date range.")

                booking = Booking.objects.create(user=user, **validated_data, status="pending", idempotency_key=idempotency_key)
                # Mark availability rows as booked (create rows as needed)
                # Create dates between start and end inclusive
                from datetime import timedelta, date
                cur = start
                to_create = []
                while cur <= end:
                    # update or create availability
                    obj, created = VehicleAvailability.objects.get_or_create(vehicle=vehicle, date=cur, defaults={"is_booked": True})
                    if not created:
                        if obj.is_booked:
                            # revert by raising error
                            raise serializers.ValidationError("Race condition: vehicle booked concurrently.")
                        obj.is_booked = True
                        obj.save()
                    cur += timedelta(days=1)
            else:
                safari = SafariPackage.objects.select_for_update().get(pk=validated_data["safari"].pk)
                # simple seat availability check
                pax = validated_data.get("pax", 1)
                if safari.seats_available is not None and safari.seats_available < pax:
                    raise serializers.ValidationError("Not enough seats available for this safari")
                # decrement seats
                safari.seats_available -= pax
                safari.save()
                booking = Booking.objects.create(user=user, **validated_data, status="pending", idempotency_key=idempotency_key)

            # Save optional booking.details (e.g., source IP, user agent)
            booking.details = booking.details or {}
            booking.details.update({
                "created_by_ip": request.META.get("REMOTE_ADDR") if request else None,
                "created_at": timezone.now().isoformat()
            })
            booking.save()

            return booking
