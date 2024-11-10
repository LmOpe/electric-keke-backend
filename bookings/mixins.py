import requests

from django.conf import settings

from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from ecoride.utils import login_to_monnify, verify_monnnify_webhook

from .models import Booking

class MonnifyMixin:
    """
    Mixin to handle Monnify authentication, retries on 401 status, and request processing.
    """
    base_url = settings.MONNIFY_URL

    def authenticate_and_post(self, url, payload):
        """
        Helper method to authenticate and post data to Monnify with retry on 401 error.
        """
        access_token = self.get_access_token()
        if not access_token:
            return Response({"error": "Unable to authenticate"}, status=status.HTTP_401_UNAUTHORIZED)

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 401:
            access_token = self.get_access_token()
            if not access_token:
                return Response({"error": "Unable to re-authenticate"}, status=status.HTTP_401_UNAUTHORIZED)
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.post(url, json=payload, headers=headers)

        return response

    def get_access_token(self):
        """
        Obtain access token for Monnify API. Can optionally force a refresh.
        """
        return login_to_monnify()

class MonnifyWebhookMixin:
    permission_classes = [AllowAny]

    def verify_webhook(self, request):
        """Verify Monnify webhook signature."""
        payload_in_bytes = request.body
        monnify_hash = request.META.get("HTTP_MONNIFY_SIGNATURE")
        return verify_monnnify_webhook(payload_in_bytes, monnify_hash, request.META)

    def handle_verification_failure(self):
        """Response for webhook verification failure."""
        return Response(
            {
                "status": "failed",
                "msg": "Webhook does not appear to come from Monnify"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def handle_success_response(self):
        """Response for successful processing."""
        return Response(
            {
                "status": "success",
                "msg": "payment processed successfully"
            },
            status=status.HTTP_200_OK
        )
