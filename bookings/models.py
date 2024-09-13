"""
Models related to Bookings
"""
# pylint: disable=missing-function-docstring

from django.db import models
from django.conf import settings

class Booking(models.Model):
    """
    Booking model for ride and delivery bookings
    """
    BOOKING_TYPE_CHOICES = [
        ('ride', 'Ride'),
        ('delivery', 'Delivery')
    ]

    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('dispute_approved', 'Dispute Approved'),
    ]

    DISPUTE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,\
                             related_name='bookings_as_user')
    rider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,\
                              related_name='bookings_as_rider')
    booking_type = models.CharField(choices=BOOKING_TYPE_CHOICES, max_length=10)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    package_details = models.TextField(null=True, blank=True)

    # Dispute fields
    is_disputed = models.BooleanField(default=False)
    dispute_status = models.CharField(max_length=50, choices=DISPUTE_STATUS_CHOICES,\
                                       null=True, blank=True)
    dispute_reason = models.TextField(null=True, blank=True)
    dispute_resolution = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.booking_type} booking by {self.user}'

    def mark_as_disputed(self, reason=None):
        self.is_disputed = True
        self.dispute_status = 'pending'
        self.dispute_reason = reason
        self.save()

    def resolve_dispute(self, resolution):
        self.is_disputed = False
        self.dispute_status = 'resolved'
        self.dispute_resolution = resolution
        self.save()

    def approve_dispute(self):
        self.status = 'dispute_approved'
        self.save()