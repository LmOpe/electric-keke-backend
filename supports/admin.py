from django.contrib import admin
from .models import ChatMessage, SupportTicket

# Register your models here.

admin.site.register([ChatMessage, SupportTicket])