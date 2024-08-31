"""Serializers for the authentication related logic"""

from rest_framework import serializers
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
