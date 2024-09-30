import jwt
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from .models import SupportTicket, ChatMessage

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self.scope['query_string'].decode().split("token=")[1]
        try:
            # Decode the JWT token to retrieve the user ID
            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user = await self.get_user(decoded_data['user_id'])
            if self.user is None:
                raise AuthenticationFailed("Invalid token")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, AuthenticationFailed):
            await self.close()
            return
        
        self.ticket_id = self.scope['url_route'].get('kwargs', {}).get('ticket_id', None)
        
        await self.accept()

        if not self.ticket_id:
            ticket = await database_sync_to_async(self.create_ticket)()
            self.ticket_id = ticket.id
            self.ticket_group_name = f"support_{self.ticket_id}"
            
            # Send ticket ID and initial message
            await self.send(text_data=json.dumps({
                'ticket_id': self.ticket_id,
                'message': "Hi! Welcome, kindly drop your message below. You will be connected to a support agent soon."
            }))
        else:
            ticket = await database_sync_to_async(self.get_ticket)(self.ticket_id)
            self.ticket_group_name = f"support_{self.ticket_id}"

        assigned_admin, user = await self.get_ticket_data(ticket)

        # Allow only the user who created the ticket and the assigned admin to access
        if self.user.is_staff:
            if assigned_admin:
                # If an admin is already assigned and another admin tries to connect, disconnect
                if assigned_admin != self.user:
                    await self.send(text_data=json.dumps({
                        'error': 'This ticket is already assigned to another admin.'
                    }))
                    await self.close()
                    return
            else:
                # If no admin is assigned, assign the current admin
                await database_sync_to_async(self.assign_admin)(ticket)
        else:
            # If it's a normal user, check if they are the owner of the ticket
            if user != self.user:
                await self.send(text_data=json.dumps({
                    'error': 'You are not authorized to access this ticket.'
                }))
                await self.close()
                return

        # Add user to the ticket's group and accept the connection
        await self.channel_layer.group_add(self.ticket_group_name, self.channel_name)

        # Fetch and send existing messages to the user or admin
        messages = await self.get_existing_messages()
        if messages:
            for message in messages:
                await self.send(text_data=json.dumps(message))

    def create_ticket(self):
        # Automatically create a ticket when the user starts a chat
        return SupportTicket.objects.create(user=self.user)
    
    def get_ticket(self, ticket_id):
        # Fetch the ticket based on the provided ticket_id
        try:
            return SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return None

    def assign_admin(self, ticket):
        # Assign the current admin to the ticket
        ticket.assigned_admin = self.user
        ticket.status = 'in_progress'
        ticket.save()

    @database_sync_to_async
    def get_ticket_data(self, ticket):
        assigned_admin = ticket.assigned_admin
        user = ticket.user

        return  assigned_admin, user
        
    @database_sync_to_async
    def get_existing_messages(self):
        # Fetch all existing messages for the ticket
        ticket = SupportTicket.objects.get(id=self.ticket_id)
        
        # Use list comprehension to create a list of message data
        return [
            {
                'message': message.message,
                'sender': message.sender.email,
                'user': message.sender.role,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for message in ticket.messages.all()
        ]
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')

        # Save the message in the database
        await database_sync_to_async(self.save_message)(message)

        # Send the message to the group
        await self.channel_layer.group_send(
            self.ticket_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.email,
                'user': self.user.role
            }
        )

    def save_message(self, message):
        # Save a chat message to the database
        ticket = SupportTicket.objects.get(id=self.ticket_id)
        ChatMessage.objects.create(ticket=ticket, sender=self.user, message=message)

    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        role = event['user']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'user': role,
        }))

    async def disconnect(self, code):
        # Leave the group on disconnect
        await self.channel_layer.group_discard(self.ticket_group_name, self.channel_name)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self.scope['query_string'].decode().split("token=")[1]
        try:
            # Decode the JWT token to retrieve the user ID
            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user = await self.get_user(decoded_data['user_id'])
            if self.user is None:
                raise AuthenticationFailed("Invalid token")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, AuthenticationFailed):
            await self.close()
            return

        # Get the user ID and form a unique notification group
        self.group_name = f"user_{self.user.id}_notifications"

        # Add the user to their unique notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Remove the user from the notification group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from the group
    async def send_notification(self, event):
        message = event['message']

        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': message
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
