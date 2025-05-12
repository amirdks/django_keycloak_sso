from django.urls import path
from django.urls.conf import include

urlpatterns = [
    path("v1/", include("django_keycloak_sso.api.backend.v1.urls")),
]
