"""Settings sepcific to local environment"""

from .settings import *

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

2024-10-20 20:20:45,245 INFO     Starting server at tcp:port=8000:interface=0.0.0.0
web-1          | 2024-10-20 20:20:45,246 INFO     HTTP/2 support not enabled (install the http2 and tls Twisted extras)
web-1          | 2024-10-20 20:20:45,246 INFO     Configuring endpoint tcp:port=8000:interface=0.0.0.0
web-1          | 2024-10-20 20:20:45,247 INFO     Listening on TCP address 0.0.0.0:8000
