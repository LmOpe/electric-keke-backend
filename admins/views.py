# pylint: disable=no-member

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Sum
from bookings.models import Booking

User = get_user_model()

class DashboardOverview(APIView):
    """
    View for getting app performance overview
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        # Users related data
        total_users = User.objects.count()
        total_active_users = User.objects.filter(is_active=True).count()
        total_inactive_users = total_users - total_active_users

        # Rides and Deliveries related data
        total_rides = Booking.objects.filter(booking_type='ride').count()
        total_deliveries = Booking.objects.filter(booking_type='delivery').count()

        # Earnings related data
        total_ride_earnings = Booking.objects.filter(booking_type='ride').aggregate(total_earnings=Sum('price'))['total_earnings'] or 0
        total_delivery_earnings = Booking.objects.filter(booking_type='delivery').aggregate(total_earnings=Sum('price'))['total_earnings'] or 0

        data = {
            'total_users': total_users,
            'total_active_users': total_active_users,
            'total_inactive_users': total_inactive_users,
            'total_rides': total_rides,
            'total_deliveries': total_deliveries,
            'total_ride_earnings': total_ride_earnings,
            'total_delivery_earnings': total_delivery_earnings
        }

        return Response(data)
