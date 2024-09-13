"""
All serializers for bookings app
"""
from rest_framework import serializers
from users.models import User

class RiderSerializer(serializers.ModelSerializer):
    """
    Avalaible riders serializer
    """
    class Meta:
        model = User
        fields = ['id', 'fullname', 'email', 'phone', 'address', 'state_of_residence']
