"""
Bookings related views
"""
# pylint: disable=no-member

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.models import User
from users.permissions import IsUser

from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer, BookingStatusUpdateSerializer
from .serializers import RiderSerializer

class AvailableRidersListView(generics.ListAPIView):
    """
    View for getting list of online riders
    """
    permission_classes = (IsAuthenticated, IsUser,)
    serializer_class = RiderSerializer

    def get_queryset(self):
        # Assuming `is_active` is used to determine if a rider is available
        return User.objects.filter(is_active=True, role='Rider')

# Create a new booking (either ride or delivery)
class BookingCreateView(generics.CreateAPIView):
    """
    View for creating new ride or delivery bookings
    """
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated, IsUser]

class BookingListView(generics.ListAPIView):
    """
    View for getting list of bookings
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'Rider':
            return Booking.objects.filter(rider=user)
        if user.role == 'User':
            return Booking.objects.filter(user=user)
        return Booking.objects.all()

class BookingStatusUpdateView(generics.UpdateAPIView):
    """
    View for handling booking status update
    """
    serializer_class = BookingStatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.role == 'Rider':
            return Booking.objects.filter(rider=user)
        if user.role == 'User':
            return Booking.objects.filter(user=user)

    def update(self, request, *args, **kwargs):
        booking = self.get_object()
        user = request.user
        new_status = request.data.get('status')

        if user.role == 'User':
            if new_status not in ['cancelled', 'completed']:
                return Response({'detail': 'You can only update status to cancelled or completed.'}, status=status.HTTP_400_BAD_REQUEST)

            if booking.status == 'completed' and booking.status == "completed":
                # Handle payment confirmation for the rider
                return Response({'detail': 'Booking completion confirmed successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'cancelled' and booking.status in ['accepted', 'in_progress', 'pending']:
                # Handle cancellation and notification
                # Notify rider about the cancellation
                # Handle refund if required
                booking.status = 'cancelled'
                booking.save()
                return Response({'detail': 'Booking cancelled successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'completed' and booking.status == 'in_progress':
                # Handle payment completion and notifications
                # Mark the booking as completed
                booking.status = 'completed'
                booking.save()
                return Response({'detail': 'Booking completed successfully.'}, status=status.HTTP_200_OK)

        if user.role == 'Rider':
            if new_status not in ['accepted', 'in_progress', 'cancelled', 'completed']:
                return Response({'detail': 'You can only update status to accepted, in_progress, cancelled or completed.'}, status=status.HTTP_400_BAD_REQUEST)

            if booking.status == 'completed':
                return Response({'detail': 'This booking has already been completed.'}, status=status.HTTP_400_BAD_REQUEST)

            if new_status == 'accepted' and booking.status == 'pending':
                # Notify the user that the rider accepted the booking
                booking.status = 'accepted'
                booking.save()
                return Response({'detail': 'Booking accepted successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'in_progress' and booking.status == 'accepted':
                # Notify user that the ride has started
                booking.status = 'in_progress'
                booking.save()
                return Response({'detail': 'Booking is now in progress.'}, status=status.HTTP_200_OK)

            if new_status == 'completed' and booking.status == 'in_progress':
                # Mark booking as completed
                booking.status = 'completed'
                booking.save()
                return Response({'detail': 'Booking completed successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'cancelled':
                # Handle cancellation by rider
                # Notify user about the cancellation
                booking.status = 'cancelled'
                booking.save()
                return Response({'detail': 'Booking cancelled by rider.'}, status=status.HTTP_200_OK)

        return Response({'detail': 'Invalid status update.'}, status=status.HTTP_400_BAD_REQUEST)
