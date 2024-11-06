"""Routes for the authentication views"""

from django.urls import path

from .views import RegisterView, ActivateUserView, RequestNewOTPView,\
    CustomTokenObtainPairView, ResetPasswordView, GetAuthUser,\
    LogoutView, DeleteAccountView, CustomTokenRefreshView, VerifyOTPView,\
    GoogleRedirectURIView, ChangePasswordWithOldPass, Profile


urlpatterns = [
    path('register-user/', RegisterView.as_view(), name='register_user'),
    path('activate-user/', ActivateUserView.as_view(), name='activate_user'),
    path('request-new-otp/', RequestNewOTPView.as_view(), name='request_new_otp'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    path('otp-verification/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth-user/', GetAuthUser.as_view(), name='auth_user'),
    path("google/signup/", GoogleRedirectURIView.as_view(), name="google_handle_redirect"),
    path("change-password/", ChangePasswordWithOldPass.as_view(), name="change_password"),
    path("profile/", Profile.as_view(), name="profile")
]
