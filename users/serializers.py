"""Serializers for the authentication related logic"""
# pylint: disable=too-few-public-methods
# pylint: disable=arguments-renamed
import re

from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for serializing user data"""
    re_password = serializers.CharField(write_only=True)
    message_type = serializers.ChoiceField(choices=['email', 'sms'], write_only=True)

    class Meta:
        """Meta class"""

        model = User
        fields = ['id', 'fullname', 'address', 'state_of_residence',
                  'role', 'email', 'phone', 'password', 're_password', 'message_type',\
                    'avatar_url', 'driver_license_front', 'driver_license_back']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def validate(self, data):
        password = data.get('password')
        re_password = data.get('re_password')
        
        if password != re_password:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        if len(password) < 6:
            raise serializers.ValidationError({"password": "Password must be at least 6 characters long."})
                                              
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase letter."})

        if not re.search(r'[a-z]', password):
            raise serializers.ValidationError({"password": "Password must contain at least one lowercase letter."})

        if not re.search(r'\d', password):
            raise serializers.ValidationError({"password": "Password must contain at least one digit."})

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise serializers.ValidationError({"password": "Password must contain at least one special character."})

        return data

    def create(self, validated_data):
        validated_data.pop('re_password', None)  # Remove re_password before creating the user
        validated_data.pop('message_type', None)  # Remove message_type before creating the user
        if validated_data["role"] == "Admin":
            user = User.objects.create_superuser(**validated_data)
        else:
            user = User.objects.create_user(**validated_data)
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer for obtaining auth tokens"""
    username = serializers.CharField()
    username_field = 'username'

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        try:
            if "@" in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(phone=username)
            if not user.is_active:
                raise AuthenticationFailed('User account is inactive')
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid credentials')
        except AuthenticationFailed:
            raise AuthenticationFailed('User account is inactive')
        except Exception as exc:
            raise AuthenticationFailed("Something went wrong") from exc

        user = authenticate(request=self.context.get('request'), username=username, password=password)

        if not user:
            raise AuthenticationFailed('Invalid credentials')

        # If authentication is successful, add the user to attrs
        attrs['user'] = user
        return super().validate(attrs)

    class Meta:
        """Token obtain serializer meta class"""
        fields = ['username', 'password']

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
