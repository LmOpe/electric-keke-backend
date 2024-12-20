"""
All serializers for bookings app
"""
# pylint: disable=no-member

from rest_framework import serializers

from users.models import User
from ecoride.utils import send_notification, create_payment_reference

from admins.models import NotificationMessage

from .models import Booking, Wallet, WithdrawalRequest

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
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Booking
        fields = ['id', 'booking_type', 'origin', 'destination', 'price',\
                  'package_details', 'status', "payment_reference"]

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
        payment_reference = create_payment_reference("ride", booking.id)
        booking.payment_reference = payment_reference
        booking.save()

        notification_data = {
            'type': 'new_booking_notification',
            'booking_id': booking.id,
            'booking_type': booking.booking_type,
            'destination': booking.destination,
            'origin': booking.origin,
            'price': str(booking.price),
            'payment_reference': booking.payment_reference,
            'package_details': booking.package_details,
            'passenger_name': booking.user.fullname,
            'passenger_email': booking.user.email,
            'passenger_phone': booking.user.phone,
            'passenger_address': booking.user.address,
        }

        send_notification(rider.id, notification_data)

        NotificationMessage(
            title="New ride request",
            body=f"{booking.user.fullname} booked a {booking.booking_type} with {booking.rider.fullname}"
        ).save()
        return booking

class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Booking update serializer
    """
    class Meta:
        model = Booking
        fields = ['status']

class WalletBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer for updating rider's wallet balance
    """
    class Meta:
        model = Wallet
        fields = ['balance']
        read_only_fields = ['balance']

class RequestWithdrawalSerializer(serializers.ModelSerializer):
    rider_fullname = serializers.CharField(source='rider.fullname', read_only=True)
    reference = serializers.ReadOnlyField()
    completed = serializers.ReadOnlyField()

    class Meta:
        model = WithdrawalRequest

        fields = ['rider_fullname', 'amount', 'completed', 'reference', 'bank_code',\
                  'account_number', 'currency']

    def create(self, validated_data):
        rider = self.context['request'].user
        if rider.rider_wallet.first().balance < validated_data['amount']:
            raise serializers.ValidationError("Requested amount must be less than or equal to wallet balance!!")

        payment_reference = create_payment_reference("disbursement")
        validated_data['rider'] = rider
        validated_data['reference'] = payment_reference

        return super().create(validated_data)
