# Base image
FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Workdir
WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Copy .env file into container
COPY .env /app/.env

# Optional: Run collectstatic at container start instead of build
# This avoids missing env variables issues during build
ENTRYPOINT ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn travel.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

# Expose port
EXPOSE 8000
