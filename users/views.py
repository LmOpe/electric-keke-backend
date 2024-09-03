"""User views for user authentication logics"""

# pylint: disable=no-member
# pylint: disable=bare-except

from random import randint
from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ecoride.utils import send_otp_email

from .models import OTP, User
from .serializers import UserSerializer, CustomTokenObtainPairSerializer


class RegisterView(APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user",
        request_body=UserSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="User registered successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "fullname": "John Doe",
                        "address": "123 Street, City",
                        "state_of_residence": "Kwara",
                        "role": "user",
                        "email": "john.doe@example.com",
                        "phone": "+2341234567890"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request",
                examples={
                    "application/json": {"detail": "Error message"}
                }
            ),
        }
    )

    def post(self, request):
        """Method for registering new user on post requests"""

        if request.data.get("message_type") is None:
            return Response({'detail': 'message_type value is required'},\
                            status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("password") is None or request.data.get("re_password") is None:
            return Response({'detail': 'Both password and re_password fields are required'},\
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
    """User activation with OTP verification endpoint"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Activate a user account by verifying the OTP",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id', 'otp'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description='OTP sent to the user'),
            },
            example={
                'id': 1,
                'otp': '12345'
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="OTP verified successfully, user activated.",
                examples={
                    "application/json": {
                        "detail": "OTP verified successfully, user activated."
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request - missing or invalid parameters",
                examples={
                    "application/json": {"detail": "Invalid or expired OTP."}
                }
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="User or OTP not found",
                examples={
                    "application/json": {"detail": "User not found."}
                }
            ),
        }
    )

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
            return Response({'detail': 'Invalid or expired OTP.'},\
                            status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OTP.DoesNotExist:
            return Response({'detail': 'OTP not found.'}, status=status.HTTP_404_NOT_FOUND)

class RequestNewOTPView(APIView):
    """View for sending new OTP to user upon request"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Request a new OTP for user verification",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['message_type','username'],
            properties={
                'message_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['email', 'sms'],
                    description='The type of message to send OTP. Defaults to email.'
                ),
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The email or phone number associated with the user.'
                ),
            },
            example={
                'message_type': 'email',
                'username': 'user@example.com'
            }
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="New OTP sent.",
                examples={
                    "application/json": {"detail": "New OTP sent."}
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request - missing or invalid parameters",
                examples={
                    "application/json": {"detail": "Both fields are required."}
                }
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="User or OTP not found",
                examples={
                    "application/json": {"detail": "User not found."}
                }
            ),
        }
    )

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
                return Response({'detail': 'Invalid message type. Choose either \
                                 "email" or "sms".'}, status=status.HTTP_400_BAD_REQUEST)

            otp_instance, created = OTP.objects.get_or_create(user=user)

            # Generate a new OTP if the current one is expired
            if created or not otp_instance.is_valid():
                otp_instance.generate_new_otp()

            # Send OTP based on the message_type
            if message_type == 'email':
                send_otp_email(user, otp_instance.otp)
            elif message_type == 'sms':
                return Response({'detail': 'SMS not available in development'},\
                                status=status.HTTP_404_NOT_FOUND)

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

    @swagger_auto_schema(
        operation_description="Obtain JWT access and refresh tokens using valid credentials.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username (email or phone)'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password')
            },
            example={
                'username': 'user@example.com',
                'password': 'password123'
            }
        ),
        responses={
            200: openapi.Response(
                description="Access and refresh tokens obtained successfully",
                examples={
                    "application/json": {
                        "refresh": "refresh_token",
                        "access": "access_token"
                    }
                }
            ),
            400: openapi.Response(
                description="Missing or invalid fields",
                examples={
                    "application/json": {
                        "detail": "Missing required fields"
                    }
                }
            ),
            401: openapi.Response(
                description="Invalid credentials",
                examples={
                    "application/json": {
                        "detail": "No active account found with the given credentials"
                    }
                }
            )
        }
    )

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
    @swagger_auto_schema(
        operation_description="Refresh JWT access token using a valid refresh token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token')
            },
            example={
                'refresh': 'refresh_token'
            }
        ),
        responses={
            200: openapi.Response(
                description="New access token obtained successfully",
                examples={
                    "application/json": {
                        "access": "new_access_token"
                    }
                }
            ),
            400: openapi.Response(
                description="Missing required field",
                examples={
                    "application/json": {
                        "detail": "This field is required."
                    }
                }
            ),
            401: openapi.Response(
                description="Token is blacklisted",
                examples={
                    "application/json": {
                        "detail": "Token is blacklisted",
                        "code": "token_not_valid"
                    }
                }
            )
        }
    )

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

class ResetPasswordView(APIView):
    """View to reset the user's password after OTP verification"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Reset the user's password after OTP verification.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password', 're_password'],
            properties={
                'username': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The username of the user, can be either email or phone.'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The new password for the account.'
                ),
                're_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The confirmation of the new password.'
                ),
            },
            example={
                'username': 'johndoe@example.com',
                'password': 'newpassword123',
                're_password': 'newpassword123',
            }
        ),
        responses={
            200: openapi.Response(
                description="Password has been reset successfully.",
                examples={
                    "application/json": {
                        "detail": "Password has been reset successfully."
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid input or missing required fields.",
                examples={
                    "application/json": {
                        "detail": "Passwords do not match."
                    }
                }
            ),
            404: openapi.Response(
                description="User not found.",
                examples={
                    "application/json": {
                        "detail": "User not found."
                    }
                }
            )
        }
    )

    def post(self, request):
        """Password resetting logic"""
        username = request.data.get('username')
        password = request.data.get('password')
        re_password = request.data.get('re_password')

        if not username:
            return Response({'detail': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not password or not re_password:
            return Response({'detail': 'Password and Confirm Password are required.'},\
                            status=status.HTTP_400_BAD_REQUEST)

        if password != re_password:
            return Response({'detail': 'Passwords do not match.'},\
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=username) \
                if '@' in username else User.objects.get(phone=username)
            user.set_password(password)
            user.save()

            return Response({'detail': 'Password has been reset successfully.'},\
                            status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
