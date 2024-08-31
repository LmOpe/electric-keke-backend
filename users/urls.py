"""Routes for the authentication views"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterView, ActivateUserView, RequestNewOTPView,\
    CustomTokenObtainPairView

urlpatterns = [
    path('register-user/', RegisterView.as_view(), name='register_user'),
    path('activate-user/', ActivateUserView.as_view(), name='activate_user'),
    path('request-new-otp/', RequestNewOTPView.as_view(), name='request_new_otp'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
