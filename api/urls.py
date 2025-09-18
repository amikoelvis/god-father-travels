from rest_framework.routers import DefaultRouter
from .views import payment_webhook
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path, include
from .views import (
    UserViewSet, VehicleCategoryViewSet, VehicleViewSet, VehicleAvailabilityViewSet,
    SafariPackageViewSet, SafariItineraryViewSet,
    BookingViewSet, PaymentViewSet, InvoiceViewSet,
    ReviewViewSet, NotificationViewSet, AdminLogViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'vehicle-categories', VehicleCategoryViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'vehicle-availabilities', VehicleAvailabilityViewSet)
router.register(r'safari-packages', SafariPackageViewSet)
router.register(r'safari-itineraries', SafariItineraryViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'reviews', ReviewViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'admin-logs', AdminLogViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("payments/webhook/", payment_webhook, name="payment-webhook"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
