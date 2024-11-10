"""
Bookings related views
"""
# pylint: disable=no-member
from decimal import Decimal

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import NotFound, ValidationError

from ecoride.utils import send_notification, create_payment_reference

from users.models import User
from users.permissions import IsUser

from .models import Booking, Wallet, WithdrawalRequest
from .serializers import BookingSerializer, BookingCreateSerializer, BookingStatusUpdateSerializer,\
                        RiderSerializer, WalletBalanceSerializer, RequestWithdrawalSerializer
from.mixins import MonnifyMixin, MonnifyWebhookMixin

class AvailableRidersListView(generics.ListAPIView):
    """
    View for getting list of online riders
    """
    permission_classes = (IsAuthenticated, IsUser,)
    serializer_class = RiderSerializer

    @swagger_auto_schema(
        operation_description="Get a list of online riders",
        security=[{'Bearer': []}],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="A list of available riders"
                            "Only users with the 'User' role can hit this endpoint.",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "fullname": "Jane Doe",
                            "email": "jane.doe@example.com",
                            "phone": "+2341234567890",
                            "address": "123 Street, City",
                            "state_of_residence": "Kwara"
                        },
                        {
                            "id": 2,
                            "fullname": "John Smith",
                            "email": "john.smith@example.com",
                            "phone": "+2349876543210",
                            "address": "456 Avenue, City",
                            "state_of_residence": "Lagos"
                        }
                    ]
                }
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Unauthorized",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            ),
        }
    )

    def get_queryset(self):
        return User.objects.filter(
            is_active=True, 
            role='Rider', 
            rider_wallet__balance__gt=-5000
            )

# Create a new booking (either ride or delivery)
class BookingCreateView(generics.CreateAPIView):
    """
    View for creating new ride or delivery bookings
    """
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated, IsUser]

    @swagger_auto_schema(
        operation_description="Create a new ride or delivery booking. "
                              "Only users with the 'User' role can hit this endpoint.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['rider', 'booking_type', 'origin', 'destination', 'price'],
            properties={
                'rider': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Email address of the rider',
                    example='rider@mail.com'
                ),
                'booking_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of the booking, e.g., 'ride' or 'delivery'",
                    example='ride'
                ),
                'origin': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Pickup location of the booking',
                    example='123 Street, City'
                ),
                'destination': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Drop-off location of the booking',
                    example='456 Avenue, City'
                ),
                'price': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Price of the booking',
                    example='1500.00'
                ),
                'package_details': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Details about the package (optional for deliveries)',
                    example='Fragile item',
                    nullable=True
                ),
            }
        ),
        security=[{'Bearer': []}],
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="Booking created successfully",
                examples={
                    "application/json": {
                        "id": 1,
                        "booking_type": "ride",
                        "origin": "123 Street, City",
                        "destination": "456 Avenue, City",
                        "price": "1500.00",
                        "package_details": "Fragile item",
                        "status": "pending"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request due to validation errors",
                examples={
                    "application/json": {
                        "rider": "No rider found with the provided email."
                    }
                }
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Authentication required or invalid token",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Handles the creation of a new booking.
        
        Possible scenarios:
        - **201 Created**: Successfully creates a new ride or delivery booking.
        - **400 Bad Request**: Invalid data provided, such as incorrect rider email or missing fields.
        - **401 Unauthorized**: Authentication credentials are missing or invalid.
        """
        return super().post(request, *args, **kwargs)

class BookingListView(generics.ListAPIView):
    """
    View for getting list of bookings
    """
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get list of bookings for the authenticated user",
        security=[{'Bearer': []}],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="List of bookings related to the authenticated user",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "user": 1,
                            "rider": 2,
                            "booking_type": "ride",
                            "origin": "123 Main Street",
                            "destination": "456 Elm Street",
                            "price": 10.50,
                            "status": "pending",
                            "created_at": "2024-09-13T12:00:00Z",
                            "updated_at": "2024-09-13T12:00:00Z",
                            "package_details": None,
                            "is_disputed": False,
                            "dispute_status": None,
                            "dispute_reason": None,
                            "dispute_resolution": None
                        }
                    ]
                }
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Unauthorized",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            ),
        }
    )

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

    @swagger_auto_schema(
            operation_description="Update the status of a booking",
            request_body=BookingStatusUpdateSerializer,
            security=[{'Bearer': []}],
            responses={
                status.HTTP_200_OK: openapi.Response(
                    description="Status updated successfully",
                    examples={
                        "application/json": {
                            "detail": "Booking accepted successfully."
                        }
                    }
                ),
                status.HTTP_400_BAD_REQUEST: openapi.Response(
                    description="Invalid status update or unauthorized action",
                    examples={
                        "application/json": {
                            "detail": "You can only update status to cancelled or completed."
                        }
                    }
                ),
                status.HTTP_401_UNAUTHORIZED: openapi.Response(
                    description="Unauthorized",
                    examples={
                        "application/json": {
                            "detail": "Authentication credentials were not provided."
                        }
                    }
                ),
                status.HTTP_404_NOT_FOUND: openapi.Response(
                    description="Booking not found",
                    examples={
                        "application/json": {
                            "detail": "Booking not found."
                        }
                    }
                ),
            }
        )

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

            if booking.status == 'completed' and new_status == "completed":
                # Handle payment confirmation for the rider
                return Response({'detail': 'Booking completion confirmed successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'cancelled' and booking.status in ['accepted', 'in_progress', 'pending']:
                # Handle cancellation and notify rider
                booking.status = 'cancelled'
                booking.save()

                # Notify the rider about cancellation
                notification_data = {
                    'type': 'booking_cancelled',
                    'booking_id': booking.id,
                    'message': f"Booking {booking.id} has been cancelled by the user.",
                }
                send_notification(booking.rider.id, notification_data)
                
                return Response({'detail': 'Booking cancelled successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'completed' and booking.status == 'in_progress':
                # Mark the booking as completed
                booking.status = 'completed'
                booking.save()

                # Notify the rider that the booking is completed
                notification_data = {
                    'type': 'booking_completed',
                    'booking_id': booking.id,
                    'message': f"Booking {booking.id} has been completed by the user.",
                }
                send_notification(booking.rider.id, notification_data)

                return Response({'detail': 'Booking completed successfully.'}, status=status.HTTP_200_OK)

        # Rider role actions
        if user.role == 'Rider':
            if new_status not in ['accepted', 'in_progress', 'cancelled', 'completed']:
                return Response({'detail': 'You can only update status to accepted, in_progress, cancelled or completed.'}, status=status.HTTP_400_BAD_REQUEST)

            if booking.status == 'completed':
                return Response({'detail': 'This booking has already been completed.'}, status=status.HTTP_400_BAD_REQUEST)

            if new_status == 'accepted' and booking.status == 'pending':
                # Update status to accepted and notify user
                booking.status = 'accepted'
                booking.save()

                # Notify the user that the booking was accepted
                notification_data = {
                    'type': 'booking_accepted',
                    'booking_id': booking.id,
                    'message': f"Your booking {booking.id} has been accepted by the rider.",
                }
                send_notification(booking.user.id, notification_data)

                return Response({'detail': 'Booking accepted successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'in_progress' and booking.status == 'accepted':
                # Update status to in_progress and notify user
                booking.status = 'in_progress'
                booking.save()

                # Notify the user that the booking is in progress
                notification_data = {
                    'type': 'booking_in_progress',
                    'booking_id': booking.id,
                    'message': f"Your booking {booking.id} is now in progress.",
                }
                send_notification(booking.user.id, notification_data)

                return Response({'detail': 'Booking is now in progress.'}, status=status.HTTP_200_OK)

            if new_status == 'completed' and booking.status == 'in_progress':
                # Mark the booking as completed
                booking.status = 'completed'
                booking.save()

                # Notify the user that the booking is completed
                notification_data = {
                    'type': 'booking_completed',
                    'booking_id': booking.id,
                    'message': f"Your booking {booking.id} has been completed.",
                }
                send_notification(booking.user.id, notification_data)

                return Response({'detail': 'Booking completed successfully.'}, status=status.HTTP_200_OK)

            if new_status == 'cancelled':
                # Update status to cancelled and notify user
                booking.status = 'cancelled'
                booking.save()

                # Notify the user that the booking was cancelled by the rider
                notification_data = {
                    'type': 'booking_cancelled_by_rider',
                    'booking_id': booking.id,
                    'message': f"Your booking {booking.id} has been cancelled by the rider.",
                }
                send_notification(booking.user.id, notification_data)

                return Response({'detail': 'Booking cancelled by rider.'}, status=status.HTTP_200_OK)

        return Response({'detail': 'Invalid status update.'}, status=status.HTTP_400_BAD_REQUEST)

class CashPaymentView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Wallet.objects.all()
    serializer_class = WalletBalanceSerializer

    @swagger_auto_schema(
        operation_description="Update the rider's wallet balance for a cash payment. "
                              "Riders request means payment is disputed hence, reverse the withdrawal; users request withdraws the\
                                  commission of the ride from the rider's wallet plus a notification sent to the rider.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Amount paid in cash'),
            },
            required=['amount']
        ),
        security=[{'Bearer': []}],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Wallet updated successfully",
                examples={
                    "application/json": {
                        "balance": "new_balance"
                    }
                }
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Invalid amount or bad request",
                examples={
                    "application/json": {
                        "detail": "Invalid amount provided."
                    }
                }
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Unauthorized",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Booking not found",
                examples={
                    "application/json": {
                        "detail": "Booking with the given ID does not exist."
                    }
                }
            ),
        }
    )

    def get_object(self):
        queryset = self.get_queryset()
        look_up_value = self.kwargs[self.lookup_field]
        user = self.request.user
        booking = None
        try:
            if user.role == "Rider":
                booking = Booking.objects.get(rider = user, id=look_up_value)
            elif user.role == "User":
                booking = Booking.objects.get(user= user, id=look_up_value)
        except Booking.DoesNotExist as exc:
            raise NotFound("Bookings with the given id does not exist!") from exc

        obj = get_object_or_404(queryset, rider=booking.rider)
        self.check_object_permissions(self.request, obj)
        return obj
    
    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.save()
        amount = self.request.data.get("amount")
        look_up_value = self.kwargs[self.lookup_field]
        booking = Booking.objects.get(id= look_up_value)
        if amount is not None:
            try:
                amount = float(amount)
                commission = Decimal(amount * 0.3)

                if user.role == "Rider":
                    instance.deposit(commission)
                    booking.paid = False
                    booking.save()

                elif user.role == "User":
                    instance.withdraw(commission)
                    booking.paid = True
                    booking.save()

                    notification_data = {
                        'type': 'payment_by_cash',
                        'booking_id': booking.id,
                        'message': f"Please confirm your passenger {booking.user.fullname} for booking {booking.id}\
                            has paid the sum of {amount}",
                    }
                    send_notification(booking.rider.id, notification_data)
            except ValueError as exc:
                raise ValueError("Invalid amount provided") from exc
        else:
            raise ValidationError("Amount cannot be none")
        
        return super().perform_update(serializer)

class MonnifyTransactionWebhookView(MonnifyWebhookMixin, generics.CreateAPIView):
    queryset = Booking.objects.all()

    def post(self, request, *args, **kwargs):
        if not self.verify_webhook(request):
            return self.handle_verification_failure()

        data = request.data.get("eventData")
        event_type = request.data.get("eventType")

        if event_type == "SUCCESSFUL_TRANSACTION":
            payment_status = data['paymentStatus']
            amount_paid = Decimal(data['amountPaid'])
            payment_reference = data['paymentReference']
            rider_commission = amount_paid - (amount_paid * Decimal(0.3))

            if payment_status == "PAID":
                try:
                    booking = Booking.objects.get(payment_reference=payment_reference)
                except Booking.DoesNotExist:
                    return Response(
                        {
                            "status": "failed",
                            "msg": "Product or service with the payment reference could not be found"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                wallet = booking.rider.rider_wallet.first()
                wallet.deposit(rider_commission)
                wallet.save()
                booking.paid = True
                booking.save()

        return self.handle_success_response()

class MonnifyDisbursementWebhookView(MonnifyWebhookMixin, generics.CreateAPIView):
    queryset = Booking.objects.all()

    def post(self, request, *args, **kwargs):
        if not self.verify_webhook(request):
            return self.handle_verification_failure()

        data = request.data.get("eventData")
        event_type = request.data.get("eventType")

        if event_type == "SUCCESSFUL_DISBURSEMENT":
            disbursement_status = data['status']
            amount = Decimal(data['amount'])
            disbursement_reference = data['reference']

            if disbursement_status == "SUCCESS":
                try:
                    withdrawal_request = WithdrawalRequest.objects.get(reference=disbursement_reference)
                except WithdrawalRequest.DoesNotExist:
                    return Response(
                        {
                            "status": "failed",
                            "msg": "Product or service with the disbursement reference could not be found"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                rider_wallet = withdrawal_request.rider.rider_wallet.first()
                rider_wallet.withdraw(amount)
                rider_wallet.save()
                withdrawal_request.completed = True
                withdrawal_request.save()

        return self.handle_success_response()

class InitializeTransactionAndChargeCardView(MonnifyMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_url = self.base_url
        data = request.data
        amount = data.get("amount")
        customer_name = request.user.fullname
        customer_email = request.user.email
        payment_reference = data.get("payment_reference")
        payment_description = "Payment for Ride"
        currency_code = data.get("currency_code", "NGN")
        card_details = data.get("card")

        initialize_payload = {
            "amount": amount,
            "customerName": customer_name,
            "customerEmail": customer_email,
            "paymentReference": payment_reference,
            "paymentDescription": payment_description,
            "currencyCode": currency_code,
            "contractCode": settings.MONNIFY_CONTRACT_CODE,
            "paymentMethods": ["CARD", "ACCOUNT_TRANSFER"]
        }

        init_url = f"{base_url}/api/v1/merchant/transactions/init-transaction"
        init_response = self.authenticate_and_post(init_url, initialize_payload)
        init_data = init_response.json()

        if init_response.status_code != 200 or not init_data.get("requestSuccessful"):
            return Response(init_data, status=status.HTTP_400_BAD_REQUEST)
        
        transaction_reference = init_data["responseBody"]["transactionReference"]

        charge_payload = {
            "transactionReference": transaction_reference,
            "collectionChannel": "API_NOTIFICATION",
            "card": {
                "number": card_details["number"],
                "expiryMonth": card_details["expiry_month"],
                "expiryYear": card_details["expiry_year"],
                "pin": card_details["pin"],
                "cvv": card_details["cvv"]
            }
        }

        charge_url = f"{base_url}/api/v1/merchant/cards/charge"
        charge_response = self.authenticate_and_post(charge_url, charge_payload)
        charge_data = charge_response.json()

        if charge_response.status_code == 200 and charge_data.get("requestSuccessful"):
            response_body = charge_data["responseBody"]
            return Response({
                "status": response_body["status"],
                "amount": response_body["authorizedAmount"],
                "paymentReference": response_body["paymentReference"],
                "transactionReference": response_body["transactionReference"]
            }, status=status.HTTP_200_OK)
        
        return Response(charge_data, status=status.HTTP_400_BAD_REQUEST)

class RequestWithdrawal(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = WithdrawalRequest.objects.filter(completed = False)
    serializer_class = RequestWithdrawalSerializer

class InitiateDisbursement(MonnifyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        account_number = settings.MONNIFY_ACCOUNT_NUMBER
        data = request.data
        batch_reference = create_payment_reference("batch")
        payments = data.get("payments")

        batch_payload = {
            "title": "Payment for riders",
            "batchReference": batch_reference,
            "narration": "Rider's payment",
            "sourceAccountNumber": account_number,
            "onValidationFailure": "CONTINUE",
            "notificationInterval": 25,
            "transactionList": payments
        }

        url = f"{self.base_url}/api/v2/disbursements/batch"
        response = self.authenticate_and_post(url, batch_payload)
        response_data = response.json()

        if response.status_code != 200 or not response_data.get("requestSuccessful"):
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        response_body = response_data["responseBody"]

        return Response({
            "status": response_body["batchStatus"],
            "amount": response_body["totalAmount"],
            "reference": response_body["batchReference"],
        }, status=status.HTTP_200_OK)


class AuthorizeDisbursement(MonnifyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        data = request.data
        reference = data.get("reference")
        code = data.get("code")

        payload = {
            "reference": reference,
            "authorizationCode": code
        }

        url = f"{self.base_url}/api/v2/disbursements/batch/validate-otp"
        response = self.authenticate_and_post(url, payload)
        response_data = response.json()

        if response.status_code != 200 or not response_data.get("requestSuccessful"):
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        response_body = response_data["responseBody"]

        return Response({
            "status": response_body["batchStatus"],
            "amount": response_body["totalAmount"],
            "reference": response_body["batchReference"],
        }, status=status.HTTP_200_OK)

class RequestNewOTP(MonnifyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        data = request.data
        reference = data.get("reference")

        payload = {
            "batchReference": reference,
        }

        url = f"{self.base_url}/api/v2/disbursements/batch/resend-otp"
        response = self.authenticate_and_post(url, payload)
        response_data = response.json()

        if response.status_code != 200 or not response_data.get("requestSuccessful"):
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        response_body = response_data["responseBody"]

        return Response({
            "message": response_data["responseMessage"],
            "email_recipients": response_body["emailRecipients"],
            "message": response_body["message"],
        }, status=status.HTTP_200_OK)
