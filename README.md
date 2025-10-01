# God Father Travels

A fully-featured travel booking platform built with **Django 5**, **Django REST Framework**, **PostgreSQL**, **Docker**, and **AWS S3**. The project includes JWT authentication, Swagger documentation, payment integration with Pesapal, Celery for background tasks, Redis caching, and more.

---

## Table of Contents

* [Features](#features)
* [Tech Stack](#tech-stack)
* [Getting Started](#getting-started)

  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Environment Variables](#environment-variables)
  * [Database Setup](#database-setup)
  * [Running Locally](#running-locally)
* [Docker Setup](#docker-setup)
* [API Documentation](#api-documentation)
* [Authentication](#authentication)
* [Deployment](#deployment)
* [Folder Structure](#folder-structure)
* [Caching and Background Tasks](#caching-and-background-tasks)
* [Payment Integration](#payment-integration)
* [Contributing](#contributing)
* [License](#license)

---

## Features

* RESTful APIs for all travel-related operations
* JWT-based authentication with access and refresh tokens
* Swagger documentation for easy testing and exploration
* PostgreSQL database
* File uploads using **AWS S3**
* Redis caching and Celery background tasks
* Payment integration with **Pesapal**
* Dockerized for consistent local and production environments
* Rate limiting (user/anon) using Django REST Framework throttling

---

## Tech Stack

* **Backend:** Django 5, Django REST Framework
* **Database:** PostgreSQL
* **Caching & Background Tasks:** Redis, Celery
* **File Storage:** AWS S3 via `django-storages`
* **API Documentation:** drf-spectacular (Swagger)
* **Deployment:** Docker, Render
* **Authentication:** JWT via `djangorestframework-simplejwt`

---

## Getting Started

### Prerequisites

* Python 3.11
* PostgreSQL
* Docker (optional, for containerized setup)
* Redis (optional, for caching and Celery)

---

### Installation

Clone the repository:

```bash
git clone https://github.com/your-username/god-father-travels.git
cd god-father-travels
```

---

### Environment Variables

Create a `.env` file in the project root:

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=your_region
AWS_S3_FILE_OVERWRITE=True
AWS_QUERYSTRING_AUTH=False

PESAPAL_CONSUMER_KEY=your_pesapal_key
PESAPAL_CONSUMER_SECRET=your_pesapal_secret
PESAPAL_CALLBACK_URL=http://localhost:8000/api/pesapal/callback/

REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=
```

---

### Database Setup

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

---

### Running Locally

Start the development server:

```bash
python manage.py runserver
```

Visit:

* **App homepage:** [http://localhost:8000/](http://localhost:8000/)
* **Admin panel:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
* **Swagger docs:** [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

---

## Docker Setup

Build and run the Docker container:

```bash
docker build -t god-father-travels .
docker run -p 8000:8000 god-father-travels
```

The app will be available at [http://localhost:8000/](http://localhost:8000/).

> Note: Make sure your `.env` variables are correctly set and accessible in Docker.

---

## API Documentation

Swagger/OpenAPI documentation is available at:
[http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

* Explore endpoints
* Test requests directly
* Automatically updated as API changes

---

## Authentication

JWT authentication using `djangorestframework-simplejwt`:

* **Obtain token:** `POST /api/token/`
* **Refresh token:** `POST /api/token/refresh/`
* **Use in headers:** `Authorization: Bearer <token>`

---

## Deployment

* Configured for Render (or any container host)
* Supports PostgreSQL, Redis, and S3 in production
* Environment variables for secrets and credentials

---

## Folder Structure

```
travel/             # Project root
├── api/            # Django app
├── templates/      # HTML templates (Swagger UI, emails, etc.)
├── staticfiles/    # Collected static files
├── media/          # Uploaded media files
├── travel/         # Django project settings
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## Caching and Background Tasks

* Redis used for caching queries and sessions
* Celery configured for background tasks

Start Celery worker:

```bash
celery -A travel worker -l info
```

---

## Payment Integration

* Pesapal API integrated for booking payments
* Configure keys in `.env`
* Callback URL handles payment confirmations

---

## Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m "Add feature"`
4. Push to the branch: `git push origin feature-name`
5. Open a pull request

---

## License

This project is **MIT Licensed**.
