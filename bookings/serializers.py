"""
All serializers for bookings app
"""
# pylint: disable=no-member

from rest_framework import serializers

from users.models import User
from ecoride.utils import send_notification

from .models import Booking

class RiderSerializer(serializers.ModelSerializer):
    """
    Avalaible riders serializer
    """
    class Meta:
        model = User
        fields = ['id', 'fullname', 'email', 'phone', 'address', 'state_of_residence']

class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for ride and delivery bookings
    """
    class Meta:
        model = Booking
        fields = '__all__'

class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Booking creation serializer
    """
    id = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = ['id', 'booking_type', 'origin', 'destination', 'price',\
                  'package_details', 'status']

    def create(self, validated_data):
        user = self.context['request'].user
        rider_email = self.initial_data.get('rider')
        try:
            rider = User.objects.get(email=rider_email, role='Rider')
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({"rider": "No rider found with the provided email."}) from exc

        validated_data['rider'] = rider
        validated_data['user'] = user

        # Create the booking
        booking = super().create(validated_data)

        notification_data = {
            'type': 'new_booking_notification',
            'booking_id': booking.id,
            'booking_type': booking.booking_type,
            'destination': booking.destination,
            'origin': booking.origin,
            'price': booking.price,
            'package_details': booking.package_details,
        }

        send_notification(rider.id, notification_data)

        return booking

class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Booking update serializer
    """
    class Meta:
        model = Booking
        fields = ['status']
