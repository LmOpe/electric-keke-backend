"""Serializers for the authentication related logic"""
# pylint: disable=too-few-public-methods

from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for serializing user data"""
    class Meta:
        """Meta class"""

        model = User
        fields = ['id', 'fullname', 'address', 'state_of_residence',\
                   'role', 'email', 'phone', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }
    def create(self, validated_data):
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
            raise serializers.ValidationError('Invalid credentials')

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
