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
        
        # Fetch the ticket or disconnect if invalid
        ticket = await database_sync_to_async(self.get_ticket)(self.ticket_id)
        if ticket is None:
            await self.close()
            return
        
        self.ticket_group_name = f"support_{self.ticket_id}"

        # Allow only the user who created the ticket and the assigned admin to access
        if self.user.is_staff:
            if ticket.assigned_admin:
                # If an admin is already assigned and another admin tries to connect, disconnect
                if ticket.assigned_admin != self.user:
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
            if ticket.user != self.user:
                await self.send(text_data=json.dumps({
                    'error': 'You are not authorized to access this ticket.'
                }))
                await self.close()
                return

        # Add user to the ticket's group and accept the connection
        await self.channel_layer.group_add(self.ticket_group_name, self.channel_name)

        # Fetch and send existing messages to the user or admin
        messages = await database_sync_to_async(self.get_existing_messages)()
        for message in messages:
            await self.send(text_data=json.dumps({
                'message': message.message,
                'sender': message.sender.email,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }))

        await self.accept()

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

    def get_existing_messages(self):
        # Fetch all existing messages for the ticket
        ticket = SupportTicket.objects.get(id=self.ticket_id)
        return ticket.messages.all()

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
