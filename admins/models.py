from django.db import models

# Create your models here.

class NotificationMessage(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title}"
