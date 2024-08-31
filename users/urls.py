"""Routes for the authentication views"""

from django.urls import path
from .views import RegisterView, ActivateUserView, RequestNewOTPView

urlpatterns = [
    path('register-user/', RegisterView.as_view(), name='register_user'),
    path('activate-user/', ActivateUserView.as_view(), name='activate_user'),
    path('request-new-otp/', RequestNewOTPView.as_view(), name='request_new_otp'),
]
