from rest_framework import serializers
from .models import SupportTicket, ChatMessage

class SupportTicketSerializer(serializers.ModelSerializer):
    first_message = serializers.SerializerMethodField()
    user_fullname = serializers.CharField(source='user.fullname')
    user_avatar_url = serializers.CharField(source='user.avatar_url')

    class Meta:
        model = SupportTicket
        fields = ['id', 'user_avatar_url' ,'user_fullname', 'assigned_admin', 'created_at', 'status', 'first_message']

    def get_first_message(self, obj):
        first_message = obj.messages.order_by('timestamp').first()
        if first_message:
            return MessageSerializer(first_message).data
        return None
    
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'ticket', 'sender', 'message', 'timestamp']
