from django.contrib import admin
from django.utils.html import format_html
from .models import (
    User,
    VehicleCategory,
    Vehicle,
    VehicleAvailability,
    SafariPackage,
    SafariItinerary,
    Booking,
    Payment,
    Invoice,
    Review,
    Notification,
    AdminLog
)

# -------------------------------
# 1. Custom User Admin
# -------------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'role', 'is_verified', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'phone')
    ordering = ('-created_at',)

# -------------------------------
# 2. Vehicle Categories & Vehicles
# -------------------------------
@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class VehicleAvailabilityInline(admin.TabularInline):
    model = VehicleAvailability
    extra = 1

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'seats', 'daily_rate', 'with_driver', 'is_available', 'image_tag', 'created_at')
    list_filter = ('category', 'with_driver', 'is_available')
    search_fields = ('name', 'description')
    inlines = [VehicleAvailabilityInline]

    readonly_fields = ('image_tag',)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height:auto;" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Image Preview'

# -------------------------------
# 3. Safari Packages & Itinerary
# -------------------------------
class SafariItineraryInline(admin.TabularInline):
    model = SafariItinerary
    extra = 1

@admin.register(SafariPackage)
class SafariPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'duration_days', 'base_price', 'seats_available', 'image_tag', 'created_at')
    list_filter = ('region',)
    search_fields = ('name', 'description')
    inlines = [SafariItineraryInline]

    readonly_fields = ('image_tag',)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height:auto;" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Image Preview'

@admin.register(SafariItinerary)
class SafariItineraryAdmin(admin.ModelAdmin):
    list_display = ('safari', 'day_number', 'title')
    search_fields = ('safari__name', 'title')

# -------------------------------
# 4. Bookings
# -------------------------------
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'booking_type', 'vehicle', 'safari', 'start_date', 'end_date', 'total_price', 'status', 'created_at')
    list_filter = ('booking_type', 'status')
    search_fields = ('user__email', 'vehicle__name', 'safari__name')

# -------------------------------
# 5. Payments & Invoices
# -------------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'provider', 'amount', 'currency', 'status', 'transaction_ref', 'created_at')
    list_filter = ('provider', 'status')
    search_fields = ('transaction_ref', 'booking__id')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('payment', 'pdf_url', 'issued_at')
    search_fields = ('payment__transaction_ref',)

# -------------------------------
# 6. Reviews
# -------------------------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'safari', 'vehicle', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__email', 'safari__name', 'vehicle__name')

# -------------------------------
# 7. Notifications
# -------------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__email', 'message')

# -------------------------------
# 8. Admin Logs (Audit Trail)
# -------------------------------
@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'created_at')
    search_fields = ('admin__email', 'action')
    readonly_fields = ('created_at',)
