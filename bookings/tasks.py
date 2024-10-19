import json
import redis
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Booking

# Set up Redis connection
r = redis.StrictRedis(host='redis', port=6379, db=0)

@shared_task
def send_rider_location():
   # Get all active bookings from Redis
    active_bookings = r.smembers('active_bookings')

    # Get the channel layer for WebSocket communication
    channel_layer = get_channel_layer()

    for booking_id in active_bookings:
        booking_id = booking_id.decode("utf-8")  # Convert from bytes to string

        # Retrieve the booking from the database
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            continue  # Skip if booking does not exist

        # Get the associated rider's ID
        rider_id = booking.rider.id

        # Get the associated rider's location from Redis (assuming it's stored in 'rider_<id>_location')
        rider_location = r.get(f'rider_{rider_id}_location')

        print(rider_location, "Rider location")

        if rider_location:
            rider_location_data = json.loads(rider_location.decode('utf-8'))

            async_to_sync(channel_layer.group_send)(
                f'booking_{booking_id}',
                {
                    'type': 'rider_location',  # This should match the method name expected in the consumer
                    'latitude': rider_location_data['lat'],
                    'longitude': rider_location_data['long'],
                }
            )
