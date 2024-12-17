from rest_framework import serializers

from django.contrib.auth import get_user_model

from bookings.models import Booking

from .models import NotificationMessage

User = get_user_model()

class EarningsSerializer(serializers.ModelSerializer):
    transaction_no = serializers.CharField(source='id')
    rider_name = serializers.CharField(source='rider.fullname')
    rider_email = serializers.CharField(source='rider.email')
    date = serializers.DateTimeField(source='created_at', format='%d/%m/%Y')
    
    class Meta:
        model = Booking
        fields = ['transaction_no', 'status', 'rider_name', 'rider_email', 'date', 'price']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationMessage
        fields = '__all__'
