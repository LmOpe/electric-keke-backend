"""Utility functions"""

from django.core.mail import send_mail

from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

def send_otp_email(user, otp, link_type):
    """Method for sending otp to user mail"""

    subject = 'User verification link'
    message = f'Hi there, {user.fullname}.\n Click on\
the link below to {link_type} your account.\n Link: {otp}'
    send_mail(subject, message, 'noreply@ecoride.com', [user.email])

def send_notification(user_id, message):
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}_notifications"

    # Send the notification to the group
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'message': message
        }
    )
