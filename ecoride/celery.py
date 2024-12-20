from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoride.settings')

app = Celery('ecoride')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-rider-location-every-5-seconds': {
        'task': 'bookings.tasks.send_rider_location',  # reference the task by name
        'schedule': 5.0,  # run every 5 seconds
    },
}
