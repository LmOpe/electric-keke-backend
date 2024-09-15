"""Routes for the authentication views"""

from django.urls import path

from .views import RegisterView, ActivateUserView, RequestNewOTPView,\
    CustomTokenObtainPairView, ResetPasswordView, GetAuthUser,\
    LogoutView, DeleteAccountView, CustomTokenRefreshView, VerifyOTPView


urlpatterns = [
    path('register-user/', RegisterView.as_view(), name='register_user'),
    path('activate-user/', ActivateUserView.as_view(), name='activate_user'),
    path('request-new-otp/', RequestNewOTPView.as_view(), name='request_new_otp'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    path('otp-verification', VerifyOTPView.as_view(), name='Verify_OTP'),
    path('auth-user/', GetAuthUser.as_view(), name='auth_user'),
]
