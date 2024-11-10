"""Routes for the authentication views"""

from django.urls import path, re_path

from .views import AvailableRidersListView, BookingCreateView,\
    BookingListView, BookingStatusUpdateView, CashPaymentView,\
    MonnifyTransactionWebhookView, InitializeTransactionAndChargeCardView,\
    MonnifyDisbursementWebhookView, RequestWithdrawal, InitiateDisbursement,\
    AuthorizeDisbursement, RequestNewOTP

from . import consumers

urlpatterns = [
    path('riders/', AvailableRidersListView.as_view(), name='riders'),
    path('new-booking/', BookingCreateView.as_view(), name='booking-create'),
    path('', BookingListView.as_view(), name='booking-list'),
    path('<int:pk>/status/', BookingStatusUpdateView.as_view(), \
         name='booking-status-update'),
    path('payment/cash/<int:pk>/', CashPaymentView.as_view(), name="pay-with-cash"),
    path('webhook/monnify/transaction/', MonnifyTransactionWebhookView.as_view(), name="payment-webhook"),
    path('webhook/monnify/disbursement/', MonnifyDisbursementWebhookView.as_view(), name="disbursement-webhook"),
    path("payment/card/", InitializeTransactionAndChargeCardView.as_view(), name='pay-with-card'),
    path('payment/withdrawal/', RequestWithdrawal.as_view(), name="withdraw-fund"),
    path('riders/disbursement/', InitiateDisbursement.as_view(), name="riders-bulk-payment"),
    path("riders/disbursement/authorization/", AuthorizeDisbursement.as_view(), name='authorize-disbursement'),
    path("riders/disbursement/resend-otp/", RequestNewOTP.as_view(), name='resend-otp'),
]

websocket_urlpatterns = [
    re_path(r'ws/rider/location/', consumers.RiderLocationConsumer.as_asgi()),
    re_path(r'ws/tracking/(?P<booking_id>\w+)/$', consumers.RideTrackingConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<booking_id>\w+)/$', consumers.RideChatConsumer.as_asgi()),
]
