"""User views for user authentication logics"""

# pylint: disable=no-member
# pylint: disable=bare-except

from random import randint
from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from ecoride.utils import send_otp_email

from .models import OTP, User
from .serializers import UserSerializer, CustomTokenObtainPairSerializer
from .permissions import IsRider, IsUser


class RegisterView(APIView):
    """User registration view"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Method for registering new user on post requests"""

        if request.data.get("message_type") is None:
            return Response({'detail': 'message_type value is required'},\
                            status=status.HTTP_400_BAD_REQUEST)
       
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp_instance = OTP.objects.create(user=user, otp=str(randint(10000, 99999)),\
                                              expires_at=timezone.now() + timedelta(minutes=5))

            # Determine how to send the OTP based on message_type
            message_type = request.data.get('message_type', 'email').lower()
            if message_type == 'email':
                send_otp_email(user, otp_instance.otp)
            elif message_type == 'sms':
                return Response({'detail': 'SMS not available in development'},\
                                status=status.HTTP_404_NOT_FOUND)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
     
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActivateUserView(APIView):
    """User activation with OTP verification view"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Method for verifying users OTP on post request post"""
        user_id = request.data.get('id')
        otp = request.data.get('otp')

        if not user_id or not otp:
            return Response({'detail': 'User id and OTP are required.'},\
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            otp_instance = OTP.objects.get(user=user)

            if otp_instance.otp == otp and otp_instance.is_valid():
                user.is_active = True
                user.save()
                return Response({'detail': 'OTP verified successfully, user activated.'},\
                                status=status.HTTP_200_OK)
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            return Response({'detail': 'OTP not found.'}, status=status.HTTP_404_NOT_FOUND)

class RequestNewOTPView(APIView):
    """View for sending new OTP to user upon request"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Method for sending new OTP to user on post request"""
        message_type = request.data.get('message_type', 'email').lower()
        username = request.data.get('username')

        if not username:
            return Response({'detail': f'{message_type.capitalize()} is required.'},\
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            if message_type == 'email':
                user = User.objects.get(email=username)
            elif message_type == 'sms':
                user = User.objects.get(phone=username)
            else:
                return Response({'detail': 'Invalid message type. Choose either "email" or "sms".'},\
                                status=status.HTTP_400_BAD_REQUEST)

            otp_instance, created = OTP.objects.get_or_create(user=user)

            # Generate a new OTP if the current one is expired
            if created or not otp_instance.is_valid():
                otp_instance.generate_new_otp()

            # Send OTP based on the message_type
            if message_type == 'email':
                send_otp_email(user, otp_instance.otp)
            elif message_type == 'sms':
                return Response({'detail': 'SMS not available in development'}, status=status.HTTP_404_NOT_FOUND)

            return Response({'detail': 'New OTP sent.'}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            return Response({'detail': 'OTP not found.'}, status=status.HTTP_404_NOT_FOUND)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that uses 
    the custom Token obtain serializer class
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Invalidate all tokens for the user before issuing a new one
        user = request.user
        if user.is_authenticated:
            tokens = RefreshToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.create(token=token)
                except:
                    pass
        
        return super().post(request, *args, **kwargs)

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view for blakclisting previous tokens
    """
    def post(self, request, *args, **kwargs):
        # Invalidate all tokens for the user before issuing a new one
        user = request.user
        if user.is_authenticated:
            tokens = RefreshToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.create(token=token)
                except:
                    pass
        
        return super().post(request, *args, **kwargs)