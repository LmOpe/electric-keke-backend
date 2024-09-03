"""Serializers for the authentication related logic"""
# pylint: disable=too-few-public-methods
# pylint: disable=arguments-renamed

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
                  'role', 'email', 'phone', 'password', 're_password', 'message_type']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def validate(self, data):
        password = data.get('password')
        re_password = data.get('re_password')

        if password != re_password:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        return data

    def create(self, validated_data):
        validated_data.pop('re_password', None)  # Remove re_password before creating the user
        user = User.objects.create_user(**validated_data)
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer for obtaining auth tokens"""
    username = serializers.CharField()
    username_field = 'username'

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

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
