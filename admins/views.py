# pylint: disable=no-member

from rest_framework.generics import ListAPIView
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

class UserListView(ListAPIView):
    """
    View to retrieve a list of users with filtering options.
    Allows filtering by signup date and status.
    """
    
    def get(self, request, *args, **kwargs):
        # Get query parameters
        status = request.GET.get('status')
        signup_date = request.GET.get('signup_date')
        
        # Base queryset
        queryset = User.objects.all()
        
        # Filter by status if provided
        if status:
            queryset = queryset.filter(is_active=(status == 'active'))
        
        # Filter by signup date if provided (formatted as dd/mm/yyyy)
        if signup_date:
            try:
                day, month, year = map(int, signup_date.split('/'))
                queryset = queryset.filter(created_at__date=f'{year}-{month:02d}-{day:02d}')
            except ValueError:
                return Response({"error": "Invalid date format, use dd/mm/yyyy"}, status=400)

        users = [
            {
                'fullname': user.fullname,
                'email': user.email,
                'phone': user.phone,
                'status': user.is_active,
                'id': user.id,
                'role': user.role,
                'signup_date': user.created_at.strftime('%d/%m/%Y')
            }
            for user in queryset
        ]
        return Response(users)
