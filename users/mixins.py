# pylint: disable=no-member

from rest_framework.response import Response
from rest_framework import status

from .models import User, OTP

class OTPVerificationMixin:
    def verify_otp(self, user_id, otp):
        if not user_id or not otp:
            return None, Response({'detail': 'User id and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            otp_instance = OTP.objects.get(user=user)

            if otp_instance.otp == otp and otp_instance.is_valid():
                return user, None  # OTP is valid, return user
            return None, Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return None, Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            return None, Response({'detail': 'OTP not found.'}, status=status.HTTP_404_NOT_FOUND)
