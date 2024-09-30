"""
ASGI config for ecoride project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import supports.urls

# Set the default settings module for the 'ecoride' project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoride.settings_prod' if os.getenv('DEBUG', 'False') == 'False' else 'ecoride.settings_local')

# Get the ASGI application
django_asgi_app = get_asgi_application()

# Define the ASGI application routing
application = ProtocolTypeRouter({
    "http": django_asgi_app,  # Handles HTTP requests
    "websocket": AuthMiddlewareStack(
        URLRouter(
            supports.urls.websocket_urlpatterns  # Handles WebSocket connections
        )
    ),
})
