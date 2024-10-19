from django.contrib import admin
from .models import Booking, RideChatMessage

# Register your models here.
admin.site.register([Booking, RideChatMessage])