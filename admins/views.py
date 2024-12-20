# pylint: disable=no-member

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import get_object_or_404

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from bookings.models import Booking

from .models import NotificationMessage
from .serializers import EarningsSerializer, NotificationSerializer

User = get_user_model()

class DashboardOverview(APIView):
    """
    View for getting app performance overview
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Get dashboard overview for admin",
        operation_description="Returns statistics about total users, rides, deliveries, and earnings. Accessible only by admins.",
        responses={
            200: openapi.Response(
                description="Dashboard overview data",
                examples={
                    "application/json": {
                        "total_users": 150,
                        "total_active_users": 100,
                        "total_inactive_users": 50,
                        "total_rides": 120,
                        "total_deliveries": 30,
                        "total_ride_earnings": 50000.00,
                        "total_delivery_earnings": 15000.00
                    }
                },
            ),
            403: "Forbidden. Only accessible by admins.",
            401: "Unauthorized. User not authenticated.",
        },
    )

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
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_summary="List all users with filters",
        operation_description="Returns a list of users. You can filter users by status (active/inactive) and signup date. Accessible only to admins.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by user status (active/inactive)", type=openapi.TYPE_STRING),
            openapi.Parameter('signup_date', openapi.IN_QUERY, description="Filter by signup date (dd/mm/yyyy)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="List of users",
                examples={
                    "application/json": [
                        {
                            "fullname": "John Doe",
                            "email": "john@example.com",
                            "phone": "1234567890",
                            "status": "active",
                            "id": 1,
                            "signup_date": "19/09/2024"
                        },
                        {
                            "fullname": "Jane Smith",
                            "email": "jane@example.com",
                            "phone": "9876543210",
                            "status": "inactive",
                            "id": 2,
                            "signup_date": "15/08/2023"
                        }
                    ]
                }
            ),
            400: "Invalid date format",
            403: "Forbidden. Only accessible by admins.",
            401: "Unauthorized. User not authenticated.",
        },
    )

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
                'status': "active" if user.is_active else "inactive",
                'id': user.id,
                'role': user.role,
                'signup_date': user.created_at.strftime('%d/%m/%Y')
            }
            for user in queryset
        ]
        return Response(users)

class EarningsListView(ListAPIView):
    """
    View to retrieve and filter earnings based on date and type (ride/delivery).
    Also allows searching for earnings on a specific date.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_summary="List all earnings with filters",
        operation_description="Returns a list of earnings. You can filter by date range, booking type (ride/delivery), or search for earnings on a specific date. Accessible only to admins.",
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description="Search for earnings on a specific date (dd/mm/yyyy)", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, description="Filter earnings from this date (dd/mm/yyyy)", type=openapi.TYPE_STRING),
            openapi.Parameter('date_to', openapi.IN_QUERY, description="Filter earnings up to this date (dd/mm/yyyy)", type=openapi.TYPE_STRING),
            openapi.Parameter('type', openapi.IN_QUERY, description="Filter by booking type (ride/delivery)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="List of earnings",
                examples={
                    "application/json": [
                        {
                            "transaction_no": 1,
                            "status": "completed",
                            "rider_fullname": "John Doe",
                            "rider_email": "john@example.com",
                            "date": "19/09/2024",
                            "amount": 500.00
                        },
                        {
                            "transaction_no": 2,
                            "status": "completed",
                            "rider_fullname": "Jane Smith",
                            "rider_email": "jane@example.com",
                            "date": "18/09/2024",
                            "amount": 350.00
                        }
                    ]
                }
            ),
            400: "Invalid date format",
            403: "Forbidden. Only accessible by admins.",
            401: "Unauthorized. User not authenticated.",
        },
    )

    def get(self, request, *args, **kwargs):
        # Get query parameters
        date = request.GET.get('date')  # For exact search on a single date
        date_from = request.GET.get('date_from')  # For filtering from this date
        date_to = request.GET.get('date_to')  # For filtering up to this date
        booking_type = request.GET.get('type')  # Filter by ride/delivery type
        
        # Base queryset
        queryset = Booking.objects.all()
        
        # Exact search by date (formatted as dd/mm/yyyy)
        if date:
            try:
                day, month, year = map(int, date.split('/'))
                queryset = queryset.filter(created_at__date=f'{year}-{month:02d}-{day:02d}')
            except ValueError:
                return Response({"error": "Invalid date format, use dd/mm/yyyy"}, status=400)
            except Exception:
                return Response({"error": "Invalid date format, use dd/mm/yyyy"}, status=400)
        
        # Filter by date range if provided (formatted as dd/mm/yyyy)
        if date_from and date_to:
            try:
                day_from, month_from, year_from = map(int, date_from.split('/'))
                day_to, month_to, year_to = map(int, date_to.split('/'))
                queryset = queryset.filter(
                    created_at__date__gte=f'{year_from}-{month_from:02d}-{day_from:02d}',
                    created_at__date__lte=f'{year_to}-{month_to:02d}-{day_to:02d}'
                )
            except ValueError:
                return Response({"error": "Invalid date format for filtering, use dd/mm/yyyy"}, status=400)
            except Exception:
                return Response({"error": "Invalid date format for filtering, use dd/mm/yyyy"}, status=400)

        # Filter by booking type if provided
        if booking_type:
            queryset = queryset.filter(booking_type=booking_type)

        # Prepare response data using serializer
        serializer = EarningsSerializer(queryset, many=True)
        return Response(serializer.data)

class AdminNotificationView(APIView):
    """
    View for listing unread notifications and updating the 'is_read' field of a single notification.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_summary="List all unread notifications",
        operation_description="Returns a list of all unread notifications. Accessible only to admins.",
        responses={
            200: openapi.Response(
                description="List of unread notifications",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "title": "New User Registered",
                            "message": "A new user has signed up.",
                            "is_read": False,
                            "created_at": "2024-06-01T12:00:00Z"
                        },
                        {
                            "id": 2,
                            "title": "System Update",
                            "message": "Scheduled maintenance at midnight.",
                            "is_read": False,
                            "created_at": "2024-06-01T15:00:00Z"
                        }
                    ]
                }
            ),
            403: "Forbidden. Only accessible by admins.",
            401: "Unauthorized. User not authenticated."
        }
    )

    def get(self, request, *args, **kwargs):
        """
        List all unread notifications.
        """
        queryset = NotificationMessage.objects.filter(is_read=False)
        serializer = NotificationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        """
        Update the 'is_read' field of a single notification.
        """
        notification_id = kwargs.get("pk")
        notification = get_object_or_404(NotificationMessage, id=notification_id)

        # Update 'is_read' field
        notification.is_read = True
        notification.save()

        # Return updated notification
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)
