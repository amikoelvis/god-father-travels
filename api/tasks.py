from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import boto3
from django.db import models
from django.db.models import Count, Prefetch

from .models import Payment, Booking, Invoice, Vehicle, VehicleAvailability, SafariPackage
from .serializers import VehicleSerializer, SafariPackageSerializer


# -------------------------------
# 1. Booking Emails
# -------------------------------
@shared_task(bind=True, max_retries=3)
def send_booking_email(self, booking_id):
    """Send booking confirmation email."""
    try:
        booking = Booking.objects.select_related("user").get(pk=booking_id)
    except Booking.DoesNotExist:
        return

    subject = f"Booking Confirmation – {booking.id}"
    body = f"Hello {booking.user.username},\n\nYour booking is confirmed."
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.user.email])


# -------------------------------
# 2. Invoices & Payment Emails
# -------------------------------
@shared_task(bind=True, max_retries=3)
def generate_invoice_and_email(self, payment_id):
    """Generate PDF invoice, upload to S3, email receipt."""
    try:
        payment = Payment.objects.select_related("booking", "booking__user").get(pk=payment_id)
    except Payment.DoesNotExist:
        return

    # Generate PDF invoice
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    doc.build([
        Paragraph(f"Invoice for booking {payment.booking.id}", styles['Normal']),
        Paragraph(f"Amount: {payment.amount} {payment.currency}", styles['Normal'])
    ])
    pdf_bytes = buffer.getvalue()

    # Upload to S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    key = f"invoices/{payment.transaction_ref}.pdf"
    s3.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{key}"

    # Save Invoice model
    Invoice.objects.update_or_create(payment=payment, defaults={"pdf_url": pdf_url})

    # Email receipt
    subject = f"Payment Receipt – {payment.transaction_ref}"
    body = f"Thank you for your payment of {payment.amount} {payment.currency}.\nInvoice: {pdf_url}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [payment.booking.user.email])


# -------------------------------
# 3. Cache Pre-Warming
# -------------------------------
@shared_task
def warm_featured_cache():
    """
    Pre-warm Redis cache for featured safaris and popular vehicles.
    This avoids slow queries on homepage / search endpoints.
    """
    # Featured Safari Packages
    safaris = SafariPackage.objects.filter(featured=True)\
        .prefetch_related("itinerary")[:10]
    safari_data = SafariPackageSerializer(safaris, many=True).data
    cache.set("featured_safaris_v1", safari_data, 3600)  # 1 hour

    # Popular Vehicles (by number of bookings)
    vehicles = (
        Vehicle.objects
        .annotate(bookings_count=Count("booking"))
        .order_by("-bookings_count")
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "availabilities",
                queryset=VehicleAvailability.objects.all().only("date", "is_booked")
            )
        )[:10]
    )
    vehicle_data = VehicleSerializer(vehicles, many=True).data
    cache.set("popular_vehicles_v1", vehicle_data, 1800)  # 30 minutes

    return {
        "featured_safaris_cached": len(safari_data),
        "popular_vehicles_cached": len(vehicle_data),
    }
