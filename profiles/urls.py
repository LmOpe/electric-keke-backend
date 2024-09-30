"""Routes for the driver validation"""
from django.urls import path

from .views import ValidateDriverLicense

urlpatterns = [
    path('validate-driver-license/', ValidateDriverLicense.as_view(), name="validate_driver_license"),
]
