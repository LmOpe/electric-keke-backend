"""Utility functions"""

from django.core.mail import send_mail

def send_otp_email(user, otp):
    """Method for sending otp to user mail"""

    subject = 'Your OTP Code'
    message = f'Your OTP code is {otp}.'
    send_mail(subject, message, 'noreply@ecoride.com', [user.email])
