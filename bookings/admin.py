from django.contrib import admin
from .models import Booking, RideChatMessage, Wallet, WithdrawalRequest

# Register your models here.
admin.site.register([Booking, RideChatMessage, Wallet, WithdrawalRequest])