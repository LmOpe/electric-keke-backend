from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import SupportTicket
from .serializers import SupportTicketSerializer

class UnassignedTicketListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        unassigned_tickets = SupportTicket.objects.filter(assigned_admin__isnull=True, status='open')
        serializer = SupportTicketSerializer(unassigned_tickets, many=True)
        return Response(serializer.data)
