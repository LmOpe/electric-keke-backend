"""Utility functions"""

import hashlib
import base64

from django.core.mail import send_mail
from django.utils.html import strip_tags

from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

def hash_to_smaller_int(large_int):
    # Convert the large integer to a string before hashing
    large_int_str = str(large_int)
    
    # Compute the SHA-256 hash of the string representation of the large integer
    hashed_bytes = hashlib.sha256(large_int_str.encode()).digest()
    
    # Convert the hashed bytes to an integer
    hashed_int = int.from_bytes(hashed_bytes, byteorder='big')
    
    # Generate a smaller integer by taking the modulo of a large number
    smaller_int = hashed_int % (10 ** 9)  # Restricting to a 9-digit number
    
    return smaller_int

def base64_encode(value):
    # Encode the concatenated string using Base64
    return base64.b64encode(value.encode()).decode()

def send_otp_email(user, otp_link, link_type):
    """Method for sending OTP to user's email with professional styling."""
    
    subject = 'Ecoride - Account Verification'
    action=None
    greeting=None
    footer=None

    if link_type == "activate":
        greeting = f"Dear {user.fullname},"
        action = "activate your account"
        footer = "We're excited to have you on board!"
    elif link_type == "verify":
        greeting = f"Dear {user.fullname},"
        action = "verify your account for password update"
        footer = "Please verify this to continue using our services."

    html_message = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #f4f4f4; padding: 20px; border-radius: 8px;">
                <h2 style="color: #4CAF50;">Ecoride - {action.capitalize()}</h2>
                <p>{greeting}</p>
                <p>Please use this code to {action}</p>
                <p>OTP: {otp_link}</p>
                # <p>To {action}, please click the link below:</p>
                # <a href="{otp_link}" style="color: #4CAF50; text-decoration: none; font-weight: bold;">{otp_link}</a>
                <p>If you did not request this, please ignore this email.</p>
                <p>{footer}</p>
                <p>Best regards,<br>Ecoride Team</p>
            </div>
        </body>
    </html>
    """

    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        'noreply@ecoride.com',
        [user.email],
        html_message=html_message
    )

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
