from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment, Booking, Invoice
from django.template.loader import render_to_string
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.core.files.base import ContentFile
import boto3

@shared_task(bind=True, max_retries=3)
def send_booking_email(self, booking_id):
    """Send booking confirmation email."""
    from .models import Booking
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        return

    subject = f"Booking Confirmation – {booking.id}"
    body = f"Hello {booking.user.username},\n\nYour booking is confirmed."
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.user.email])

@shared_task(bind=True, max_retries=3)
def generate_invoice_and_email(self, payment_id):
    """Generate PDF invoice, upload to S3, email receipt."""
    try:
        payment = Payment.objects.select_related("booking", "booking__user").get(pk=payment_id)
    except Payment.DoesNotExist:
        return

    # Generate simple PDF invoice
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    doc.build([Paragraph(f"Invoice for booking {payment.booking.id}", styles['Normal']),
               Paragraph(f"Amount: {payment.amount} {payment.currency}", styles['Normal'])])
    pdf_bytes = buffer.getvalue()

    # Upload to S3
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    key = f"invoices/{payment.transaction_ref}.pdf"
    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                  Key=key,
                  Body=pdf_bytes,
                  ContentType="application/pdf")
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{key}"

    # Save Invoice model
    Invoice.objects.update_or_create(payment=payment, defaults={"pdf_url": pdf_url})

    # Email receipt
    subject = f"Payment Receipt – {payment.transaction_ref}"
    body = f"Thank you for your payment of {payment.amount} {payment.currency}.\nInvoice: {pdf_url}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [payment.booking.user.email])
