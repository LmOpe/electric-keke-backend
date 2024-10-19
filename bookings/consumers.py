import json
import jwt
import redis

from django.conf import settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.exceptions import AuthenticationFailed

from .models import Booking, RideChatMessage

User = get_user_model()

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
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

class RideChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope['query_string'].decode().split("token=")[1]

        try:
            # Decode the JWT token to retrieve the user ID
            decoded_data = jwt.decode(self.token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user = await self.get_user(decoded_data['user_id'])

            if not self.user:
                raise AuthenticationFailed("Invalid user")

            self.booking_id = self.scope['url_route']['kwargs']['booking_id']
            self.booking = await self.get_booking(self.booking_id)

            if not self.booking:
                raise AuthenticationFailed("Invalid booking")

            if not self.is_user_associated_with_booking(self.user, self.booking):
                raise AuthenticationFailed("User is not associated with this booking")

            self.group_name = f'chat_{self.booking_id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            # Accept the WebSocket connection
            await self.accept()

            # Load and send the chat history for the booking when a user connects
            chat_history = await self.get_chat_history(self.booking_id)
            for chat_message in chat_history:
                await self.send(text_data=json.dumps({
                    'message': chat_message['message'],
                    'user': str(chat_message['sender__id']),
                    'role': chat_message['sender__role'],
                    'timestamp': chat_message['timestamp'].isoformat()
                }))

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, AuthenticationFailed):
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Save the message to the database
        await self.save_chat_message(self.booking_id, self.user.id, message)

        # Send the message to the group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': str(self.user.id),
                'role': self.user.role
            }
        )

    async def chat_message(self, event):
        message = event['message']
        user_id = event['user']
        role = event['role']

        await self.send(text_data=json.dumps({
            'message': message,
            'user': user_id,
            'role': role
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_booking(self, booking_id):
        try:
            return Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return None

    @database_sync_to_async
    def save_chat_message(self, booking_id, user_id, message):
        booking = Booking.objects.get(id=booking_id)
        sender = User.objects.get(id=user_id)
        return RideChatMessage.objects.create(booking=booking, sender=sender, message=message)

    @database_sync_to_async
    def get_chat_history(self, booking_id):
        # Query chat messages and include the sender's id and role
        return list(RideChatMessage.objects.filter(booking_id=booking_id)
                .order_by('timestamp')
                .values('message', 'timestamp', 'sender__id', 'sender__role'))
    
    @database_sync_to_async
    def is_user_associated_with_booking(self, user, booking):
        if user.id in (booking.rider.id, booking.user.id):
            return True
        return False