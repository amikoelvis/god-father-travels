import boto3
from django.conf import settings
from datetime import datetime, timedelta

def generate_presigned_url(file_name: str, file_type: str, expires_in=3600):
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    presigned_post = s3_client.generate_presigned_post(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=file_name,
        Fields={"Content-Type": file_type},
        Conditions=[
            {"Content-Type": file_type},
            ["content-length-range", 1, 5242880]  # 1 byte to 5MB
        ],
        ExpiresIn=expires_in,
    )

    file_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"
    return presigned_post, file_url
