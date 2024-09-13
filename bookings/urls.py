"""Routes for the authentication views"""

from django.urls import path

from .views import AvailableRidersListView

urlpatterns = [
     path('riders/', AvailableRidersListView.as_view(), name='riders'),
]
