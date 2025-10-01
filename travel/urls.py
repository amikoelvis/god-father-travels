from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import HttpResponse

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API routes
    path("api/", include("api.urls")),

    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),

    # Optional: ReDoc UI
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc"
    ),

    # Root URL
    path("", lambda request: HttpResponse("Welcome to God Father Travels!")),
]
