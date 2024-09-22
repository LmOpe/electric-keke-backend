from django.urls import path, re_path
from . import consumers

from .views import UnassignedTicketListView

urlpatterns = [
    path('tickets/unassigned/', UnassignedTicketListView.as_view(), name='unassigned-tickets'),
]


websocket_urlpatterns = [
    # Route for new chat (no ticket ID)
    re_path(r'ws/support/$', consumers.ChatConsumer.as_asgi()),

    # Route for existing chat (with ticket ID)
    re_path(r'ws/support/(?P<ticket_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]
