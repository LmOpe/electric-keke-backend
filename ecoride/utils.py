"""Utility functions"""

from django.core.mail import send_mail

def send_otp_email(user, otp, link_type):
    """Method for sending otp to user mail"""

    subject = 'User verification link'
    message = f'Hi there, {user.fullname}.\n Click on\
the link below to {link_type} your account.\n Link: {otp}'
    send_mail(subject, message, 'noreply@ecoride.com', [user.email])
