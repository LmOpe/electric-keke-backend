# Create your models here.
from django.db import models
from django.conf import settings

# Create your models here.
class Profile(models.Model):
    user_id = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    avatar = models.CharField(max_length=400, blank=True, null=True)
    driver_license = models.CharField(max_length=400, blank=True, null=True)
    document = models.CharField(max_length=400, blank=True, null=True)

    is_driver_licence_validated = models.BooleanField(default=False)
    is_document_validated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user_id}"

class PaymentDetails(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_email = models.EmailField()
    bank_code = models.IntegerField()
    account_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"