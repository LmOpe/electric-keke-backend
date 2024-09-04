"""
The Module for user authentication related models
"""

import uuid

from datetime import timedelta
from random import randint

from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Role choices
ROLE_CHOICES = (
    ('Admin', 'Admin'),
    ('Rider', 'Rider'),
    ('User', 'User'),
)

class UserManager(BaseUserManager):
    """Model manager for the User model"""

    def create_user(self, email=None, phone=None, password=None, role=None, **kwargs):
        """Function for creating user instance"""
        if email is None:
            raise TypeError('User must have an email address')
        if phone is None:
            raise TypeError('User must have a phone number')
        if password is None:
            raise TypeError('User must have a password')
        if role is None:
            raise TypeError('User must have a role')

        user = self.model(email=self.normalize_email(email),
                          phone=phone,
                          role=role,
                          **kwargs,
                          )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, phone, password, **kwargs):
        """Super user function"""
        kwargs.setdefault('role', 'admin')  # Set default role for superuser

        if kwargs.get('role') is None:
            raise ValueError('Superusers must have a role.')

        role =  kwargs.pop('role')

        user = self.create_user(email, phone, password, role, **kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """The model for storing auth user details"""

    id = models.UUIDField(primary_key=True,
                        default=uuid.uuid4,
                        auto_created=True,
                        editable=False)
    fullname = models.CharField(max_length=150)
    email = models.EmailField(db_index=True, unique=True)
    phone = models.CharField(max_length=15, unique=True)
    address = models.CharField(max_length=150)
    state_of_residence = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    # Adding related_name to avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.'
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

    def __str__(self):
        """Function to provide human-readable string for the object"""
        return f'{self.fullname} {self.email}'

class OTP(models.Model):
    """OTP model for handling user OTPs"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        """Check if OTP is still valid."""
        return timezone.now() < self.expires_at

    def generate_new_otp(self):
        """Generate a new OTP and update the expiration time."""

        self.otp = str(randint(10000, 99999))
        self.created_at = timezone.now()
        self.expires_at = self.created_at + timedelta(minutes=5)
        self.save()
