import json
import jwt
import redis

from django.conf import settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.exceptions import AuthenticationFailed

from .models import Booking

# Set up Redis connection
r = redis.StrictRedis(host='redis', port=6379, db=0)

class RiderLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the token from the query string
        self.token = self.scope['query_string'].decode().split("token=")[1]

        try:
            # Decode the JWT token to retrieve the user ID
            decoded_data = jwt.decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user = await self.get_user(decoded_data['user_id'])

            # Check if the user exists and if they are a rider
            if self.user and self.user.role == "Rider":
                # Add the rider's ID to the active riders set in Redis
                r.sadd('active_riders', str(self.user.id))

                # Accept the WebSocket connection
                await self.accept()
            else:
                # Close the connection if the user is not a rider
                raise AuthenticationFailed("User is not a rider")

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, AuthenticationFailed):
            await self.close()
            return

    async def receive(self, text_data):
        # Parse the incoming data
        data = json.loads(text_data)
        rider_lat = data['latitude']
        rider_long = data['longitude']

        # Store the rider's location in Redis
        r.set(f'rider_{self.user.id}_location', json.dumps({'lat': rider_lat, 'long': rider_long}))
        print("New locations:", rider_lat, rider_long)

    async def disconnect(self, close_code):
        # Remove the rider's ID from the active riders set in Redis when they disconnect
        r.srem('active_riders', str(self.user.id))

        # Close the WebSocket connection
        await self.close()
    
    @database_sync_to_async
    def get_user(self, user_id):
        # Retrieve the user by their ID (adjust according to your project’s user model)
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

class RideTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract the token from the query string
        self.token = self.scope['query_string'].decode().split("token=")[1]
        
        try:
            # Decode the JWT token to retrieve the user ID
            decoded_data = jwt.decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user = await self.get_user(decoded_data['user_id'])

            # Check if the user exists and has the correct role (e.g., 'user')
            if not self.user or self.user.role != "User":
                raise AuthenticationFailed("Invalid user or role")
        
            # Check if the booking exists and is associated with the user
            self.booking_id = self.scope['url_route']['kwargs']['booking_id']
            booking_user_id = await self.get_booking_user_id(self.booking_id)

            if booking_user_id != self.user.id:
                raise AuthenticationFailed("User is not associated with this booking")
            
            # Join the tracking group
            self.group_name = f'booking_{self.booking_id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            # Add the booking ID to active bookings in Redis
            r.sadd('active_bookings', str(self.booking_id))

            # Accept the WebSocket connection
            await self.accept()

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, AuthenticationFailed):
            await self.close()
            return

    async def disconnect(self, close_code):
        # Remove the booking ID from Redis active bookings
        r.srem('active_bookings', str(self.booking_id))

        # Leave the tracking group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def rider_location(self, event):
        # Send the rider's location to the WebSocket client
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude'],
        }))

    # Helper function to fetch the booking asynchronously
    @database_sync_to_async
    def get_booking_user_id(self, booking_id):
        try:
            return Booking.objects.get(id=booking_id).user.id
        except Booking.DoesNotExist:
            return None

    # Helper function to fetch the user asynchronously
    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
