"""
Bookings related views
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from users.models import User
from users.permissions import IsUser
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
