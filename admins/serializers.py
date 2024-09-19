from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserListSerializer(serializers.ModelSerializer):
    signup_date = serializers.DateTimeField(source='created_at', format="%d/%m/%Y")
    
    class Meta:
        model = User
        fields = ['id', 'fullname', 'email', 'phone', 'status', 'signup_date']
