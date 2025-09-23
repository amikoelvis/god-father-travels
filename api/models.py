from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import JSONField
from django.core.validators import FileExtensionValidator
import uuid


# -------------------------------
# 1. User & Roles
# -------------------------------
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=[
            ("customer", "Customer"),
            ("admin", "Admin"),
            ("staff", "Staff"),
        ],
        default="customer",
    )
    is_verified = models.BooleanField(default=False)  # email/phone verification
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


# -------------------------------
# 2. Vehicles (Car Hire)
# -------------------------------
class VehicleCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)  # SUV, Safari Jeep, Luxury Van
    description = models.TextField(blank=True, null=True)


class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(VehicleCategory, on_delete=models.CASCADE, related_name="vehicles")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    seats = models.IntegerField()
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    with_driver = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to="vehicles/",  # folder path inside your storage bucket
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class VehicleAvailability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    is_booked = models.BooleanField(default=False)


# -------------------------------
# 3. Safari Packages
# -------------------------------
class SafariPackage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField()
    region = models.CharField(max_length=100)  # e.g., Bwindi, Murchison Falls
    duration_days = models.IntegerField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    seats_available = models.IntegerField()
    image = models.ImageField(
        upload_to="safaris/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]
    )
    created_at = models.DateTimeField(auto_now_add=True)


class SafariItinerary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    safari = models.ForeignKey(SafariPackage, on_delete=models.CASCADE, related_name="itinerary")
    day_number = models.IntegerField()
    title = models.CharField(max_length=150)
    description = models.TextField()


# -------------------------------
# 4. Bookings (Car Hire & Safari)
# -------------------------------
class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(
        max_length=20,
        choices=[("vehicle", "Vehicle"), ("safari", "Safari")],
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, blank=True, null=True)
    safari = models.ForeignKey(SafariPackage, on_delete=models.SET_NULL, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    pax = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
            ("completed", "Completed"),
        ],
        default="pending",
    )
    idempotency_key = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

# -------------------------------
# 5. Payments & Invoices
# -------------------------------
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=50)  # Stripe, PayPal, Flutterwave, Paystack
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="UGX")
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
    )
    transaction_ref = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="invoice")
    pdf_url = models.URLField(blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)


# -------------------------------
# 6. Reviews & Ratings
# -------------------------------
class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    safari = models.ForeignKey(SafariPackage, on_delete=models.CASCADE, blank=True, null=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, blank=True, null=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1)  # e.g., 4.5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------------
# 7. Notifications & Messages
# -------------------------------
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------------
# 8. Admin Logs (Audit Trail)
# -------------------------------
class AdminLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_logs")
    action = models.CharField(max_length=200)
    details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
