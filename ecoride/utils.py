"""Utility functions"""

import hashlib
import base64
import uuid
import hmac

from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings

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

def create_payment_reference(ride_id):
    return f"ride_{ride_id}_{uuid.uuid4().hex}"

def verify_hash(payload_in_bytes, monnify_hash):
    """
    Recieves the monnify payload in bytes and perform a SHA-512 hash
    with your secret key which is also encoded in byte.
    uses hmac.compare_digest rather than "=" sign as the former helps
    to prevent timing attacks.
    """
    secret_key_bytes = settings.MONNIFY_SECRET.encode("utf-8")
    hash_in_bytes = hmac.new(
        secret_key_bytes, msg=payload_in_bytes, digestmod=hashlib.sha512
    )
    hash_in_hex = hash_in_bytes.hexdigest()
    return hmac.compare_digest(hash_in_hex, monnify_hash)

def get_sender_ip(headers):
    """
    Get senders' IP address, by first checking if your API server
    is behind a proxy by checking for HTTP_X_FORWARDED_FOR
    if not gets sender actual IP address using REMOTE_ADDR
    """
    x_forwarded_for = headers.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
   
    return headers.get("REMOTE_ADDR")

def verify_monnnify_webhook(payload_in_bytes, monnify_hash, headers):
    """
    The interface that does the verification by calling necessary functions.
    Though everything has been tested to work well, but if you have issues
    with this function returning False, you can remove the get_sender_ip
    function to be sure that the verify_hash is working, then you can check
    what header contains the IP address.
    """
    return get_sender_ip(headers) == settings.MONNIFY_IP and verify_hash(
        payload_in_bytes, monnify_hash
    )
