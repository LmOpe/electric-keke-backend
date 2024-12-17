"""User views for user authentication logics"""

# pylint: disable=no-member
# pylint: disable=bare-except
import requests

from random import randint
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseRedirect

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ecoride.utils import send_otp_email, hash_to_smaller_int
from ecoride.settings import BACKEND_URL

from admins.models import NotificationMessage

from  bookings.models import Wallet

from .models import OTP, User
from .serializers import UserSerializer, CustomTokenObtainPairSerializer
from .mixins import OTPVerificationMixin

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
                # link = f"{BASE_URL}/authentication/verification/?verificationType=activate&email={user.email}&id={user.id}&otp={otp_instance.otp}"
                send_otp_email(user, otp_instance.otp, "activate")
            elif message_type == 'sms':
                return Response({'detail': 'SMS not available in development'},\
                                status=status.HTTP_404_NOT_FOUND)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActivateUserView(APIView, OTPVerificationMixin):
    """Activate user account after verifying the OTP."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Activate a user account by verifying the OTP.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id', 'otp'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_STRING, description='User ID'),
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description='OTP sent to the user'),
            },
            example={'id': 1, 'otp': '12345'}
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(description="User activated successfully."),
            status.HTTP_400_BAD_REQUEST: openapi.Response(description="Invalid or expired OTP."),
            status.HTTP_404_NOT_FOUND: openapi.Response(description="User or OTP not found."),
        }
    )
    def post(self, request):
        user_id = request.data.get('id')
        otp = request.data.get('otp')

        user, error_response = self.verify_otp(user_id, otp)
        if error_response:
            return error_response

        if user.is_active:
            return Response({'detail': 'User is already active.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()
        # Create Wallet instance for each rider
        if user.role == "Rider":
            Wallet(rider=user).save()

        NotificationMessage(
            title="New user registered",
            body=f"User, {user.fullname} just signed up and activated their account"
        ).save()
        return Response({'detail': 'User activated successfully.'}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView, OTPVerificationMixin):
    """Check if OTP is valid without activating user"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Check if the provided OTP is valid.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['id', 'otp'],
            properties={
                'id': openapi.Schema(type=openapi.TYPE_STRING, description='User ID'),
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description='OTP sent to the user'),
            },
            example={'id': 1, 'otp': '12345'}
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(description="OTP verified successfully."),
            status.HTTP_400_BAD_REQUEST: openapi.Response(description="Invalid or expired OTP."),
            status.HTTP_404_NOT_FOUND: openapi.Response(description="User or OTP not found."),
        }
    )
    def post(self, request):
        user_id = request.data.get('id')
        otp = request.data.get('otp')

        _, error_response = self.verify_otp(user_id, otp)
        if error_response:
            return error_response

        return Response({'detail': 'OTP verified successfully.'}, status=status.HTTP_200_OK)


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
                    "application/json": {"detail": "New OTP sent.", "user_id": 3}
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

            try:
                otp_instance = OTP.objects.get(user=user)
            except OTP.DoesNotExist:
                otp_instance = OTP.objects.create(user=user, otp=str(randint(10000, 99999)),\
                                              expires_at=timezone.now() + timedelta(minutes=5))
            # Generate a new OTP if the current one is expired
            if not otp_instance.is_valid():
                otp_instance.generate_new_otp()

            # Send OTP based on the message_type
            if message_type == 'email':
                # link = f"{BASE_URL}/authentication/verification/?verificationType=update-password&email={user.email}&id={user.id}&otp={otp_instance.otp}"
                send_otp_email(user, otp_instance.otp, "verify")
            elif message_type == 'sms':
                return Response({'detail': 'SMS not available in development'},\
                                status=status.HTTP_404_NOT_FOUND)

            return Response({'detail': 'New OTP sent.', "user_id": user.id}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
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
            tokens = OutstandingToken.objects.filter(user=user)
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
            tokens = OutstandingToken.objects.filter(user=user)
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
        
class ChangePasswordWithOldPass(APIView):
    """
    Change authenticated user's Password
    """
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Chnage the password for authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['old_password', 'new_password', 're_new_password'],
            properties={
                'old_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The old password for the user'
                ),
                'new_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The new password for the account.'
                ),
                're_new_password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The confirmation of the new password.'
                ),
            },
            example={
                'old_password': 'oldpassword123',
                'new_password': 'newpassword123',
                're_new_password': 'newpassword123',
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
            401: openapi.Response(
                description="Invalid credentials",
                examples={
                    "application/json": {
                         "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )

    def put(self, request, *args, **kwargs):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        re_new_password = request.data.get("re_new_password")
        user = request.user

        if not old_password or not new_password or not re_new_password:
            return Response({"detail: All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(old_password):
            return Response({"erorr": "Old password is wrong!"}, status=status.HTTP_401_UNAUTHORIZED)

        if new_password != re_new_password:
            return Response({"error": "Passwords do not match!"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({"detail": "Password changed successfully"}, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Logout the user and expire their tokens.",
        responses={
            200: openapi.Response(
                description="User successfully logged out",
                examples={
                    "application/json": {
                        "detail": "Successfully logged out."
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized request",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Blacklist the refresh token on logout.
        """
        user = request.user
        try:
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.create(token=token)
                except Exception as e:
                    pass 
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"detail": "Refresh field is required."}, status=status.HTTP_400_BAD_REQUEST)
        
class DeleteAccountView(APIView):
    """
    Delete user account and blacklist all tokens
    """
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Delete the user's account and expire all tokens associated with the account.",
        responses={
            200: openapi.Response(
                description="Account successfully deleted",
                examples={
                    "application/json": {
                        "detail": "Account deleted successfully."
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid request",
                examples={
                    "application/json": {
                        "detail": "Could not delete account."
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized request",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )

    def delete(self, request, *args, **kwargs):
        """
        Delete the user's account and blacklist their tokens.
        """
        user = request.user
        try:
            # Blacklist all the user's tokens
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.create(token=token)
                except Exception as e:
                    pass 
            # Delete the user
            user.delete()
            return Response({"detail": "Account deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Could not delete account."}, status=status.HTTP_400_BAD_REQUEST)

class GetAuthUser(APIView):
    """
    View to retrieve the authenticated user's information.
    """
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Retrieve information about the authenticated user.",
        responses={
            200: openapi.Response(
                description="Authenticated user's information retrieved successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "phone_number": "09012345678",
                        "email": "user@example.com",
                        "fullname": "John Doe",
                        "address": "123 Main St",
                        "state_of_residence": "Lagos",
                        "role": "User"
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized request",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )
    def get(self, request):
        """
        Get function to retreive authenticated user's
        information
        """
        user = request.user
        user_data = {
            'id': user.id,
            'phone_number': user.phone,
            'email': user.email,
            'fullname': user.fullname,
            'address': user.address,
            'state_of_residence': user.state_of_residence,
            'role': user.role,
            'wallet_balance': user.rider_wallet.first().balance if user.role == "Rider" else "Not applicable",
            'avatar': user.avatar_url,
            'driver_license_front': user.driver_license_front,
            'driver_license_back': user.driver_license_back
            
        }
        return Response(user_data, status=status.HTTP_200_OK)

class GoogleRedirectURIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Extract the authorization code from the request URL
        code = request.GET.get('code')
        
        if code:
            # Prepare the request parameters to exchange the authorization code for an access token
            token_endpoint = 'https://oauth2.googleapis.com/token'
            token_params = {
                'code': code,
                'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
                'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
                'redirect_uri': f'{BACKEND_URL}/api/v1/auth/google/signup',  # Must match the callback URL configured in your Google API credentials
                'grant_type': 'authorization_code',
            }
            
            # Make a POST request to exchange the authorization code for an access token
            try:
                response = requests.post(token_endpoint, data=token_params)
            except:
                return HttpResponseRedirect(f"{settings.BASE_URL}/onboarding/registration")
            
            if response.status_code == 200:
                access_token = response.json().get('access_token')
                
                if access_token:
                    # New People API endpoint for fetching detailed user profile information
                    profile_endpoint = 'https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses,phoneNumbers,addresses'
                    headers = {'Authorization': f'Bearer {access_token}'}
                    # Make a request to the People API to get the user's detailed profile
                    profile_response = requests.get(profile_endpoint, headers=headers)
                    user = None
                    if profile_response.status_code == 200:
                        data = {}
                        profile_data = profile_response.json()
                        
                        # You can now extract additional fields, for example:
                        name = profile_data.get('names', [{}])[0].get('displayName', 'Unknown')
                        email = profile_data.get('emailAddresses', [{}])[0].get('value', 'Unknown')
                        phone_number = profile_data.get('phoneNumbers', [{}])[0].get('value', 'Not provided')
                        address = profile_data.get('addresses', [{}])[0].get('formattedValue', 'Not provided')
                        
                        # Proceed with user creation or login
                        uid = hash_to_smaller_int(profile_data['resourceName'])  # Replace 'id' with 'resourceName'

                        try:
                            user = User.objects.get(id=uid)
                            
                            refresh = RefreshToken.for_user(user)
                            data['access'] = str(refresh.access_token)
                            data['refresh'] = str(refresh)
                            frontend_redirect_url = f"{settings.BASE_URL}/google-signup?access_token={data['access']}&refresh_token={data['refresh']}"

                            return HttpResponseRedirect(frontend_redirect_url)

                        except User.DoesNotExist:
                            user = User.objects.create_user(id=uid,fullname=name, phone=phone_number,\
                                                address=address, state_of_residence=address,role="User",
                                                email=f"{email}-{uid}", password='@Temp123', is_active=True)
                            
                            refresh = RefreshToken.for_user(user)
                            data['access'] = str(refresh.access_token)
                            data['refresh'] = str(refresh)
                            frontend_redirect_url = f"{settings.BASE_URL}/google-signup?access_token={data['access']}&refresh_token={data['refresh']}"
                            #return Response({"Access": data['access'], "Refresh": data['refresh']}, status.HTTP_200_OK)
                            return HttpResponseRedirect(frontend_redirect_url)
                        
        return Response({}, status.HTTP_400_BAD_REQUEST)

class Profile(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Change any of the user's profile data. All fields are optional",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'fullname': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='New user"s fullname.'
                ),'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='New user"s email.'
                ),
                'phone': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='New user"s phone number'
                ),
                'address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='New user"s address'
                ),
                'state': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='New user"s state of residence.'
                )
            },
            example={
                'fullname': 'John Doe',
                'email': 'john.doe@ecoride.com',
                'state': 'Texas',
            }
        ),
        responses={
            204: openapi.Response(
                description="No content"
            ),
            401: openapi.Response(
                description="Invalid credentials",
                examples={
                    "application/json": {
                        "detail": "Given token not valid for any token type"
                    }
                }
            )
        }
    )

    def put(self, request, *args, **kwargs):
        fullname = request.data.get("fullname")
        email = request.data.get("email")
        phone = request.data.get("phone")
        address = request.data.get("address")
        state = request.data.get("state")
        avatar_url = request.data.get("avatar_url")
        driver_license_front = request.data.get("driver_license_front")
        driver_license_back = request.data.get("driver_license_back")
        user = request.user
        def check_and_change(field_name, new_value, user):
            if new_value is not None and hasattr(user, field_name):
                setattr(user, field_name, new_value)
            
        check_and_change("fullname", fullname, user)
        check_and_change("email", email, user)
        check_and_change("phone", phone, user)
        check_and_change("address", address, user)
        check_and_change("avatar_url", avatar_url, user)
        check_and_change("driver_license_front", driver_license_front, user)
        check_and_change("driver_license_back", driver_license_back, user)
        check_and_change("state_of_residence", state, user)

        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)