"""
Custom user authenticationlogic to support 
user login with email or phone number
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailOrPhoneBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either their email or phone number.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        try:
            # Try to get the user using email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                # Try to get the user using phone
                user = User.objects.get(phone=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None