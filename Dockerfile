# -------------------------------
# Base image
# -------------------------------
FROM python:3.11-slim

# -------------------------------
# Environment
# -------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------------------------------
# Working directory
# -------------------------------
WORKDIR /app

# -------------------------------
# System dependencies
# -------------------------------
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        libpq-dev \
        curl \
        pkg-config \
        libcairo2-dev \
        libgirepository1.0-dev \
        gir1.2-gtk-3.0 \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Copy requirements first (caching)
# -------------------------------
COPY requirements.txt /app/

# -------------------------------
# Install Python dependencies
# -------------------------------
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# -------------------------------
# Copy project code
# -------------------------------
COPY . /app/

# -------------------------------
# Make wait-for-it.sh executable (optional)
# -------------------------------
RUN chmod +x wait-for-it.sh

# -------------------------------
# Expose port
# -------------------------------
EXPOSE 8000

# -------------------------------
# Run migrations then start Gunicorn
# -------------------------------
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn travel.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
