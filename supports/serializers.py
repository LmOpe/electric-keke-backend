from rest_framework import serializers
from .models import SupportTicket, ChatMessage

class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['id', 'user', 'admin', 'created_at', 'status']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'ticket', 'sender', 'message', 'timestamp']
