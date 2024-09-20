"""Settings sepcific to Production environment"""

from .settings import *

# Load environment variables from .env file
load_dotenv()

# Local settings
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", 'localhost,127.0.0.1,.vercel.app,.now.sh,https://electric-keke-backend.vercel.app/,https://electric-keke-backend-julp8kypl-lmopes-projects.vercel.app/').split(',')

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://electric-keke-frontend.vercel.app",
]
