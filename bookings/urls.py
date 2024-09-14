"""Routes for the authentication views"""

from django.urls import path

from .views import AvailableRidersListView, BookingCreateView,\
    BookingListView, BookingStatusUpdateView

urlpatterns = [
    path('riders/', AvailableRidersListView.as_view(), name='riders'),
    path('new-booking/', BookingCreateView.as_view(), name='booking-create'),
    path('', BookingListView.as_view(), name='booking-list'),
    path('<int:pk>/status/', BookingStatusUpdateView.as_view(), \
         name='booking-status-update'),
]
