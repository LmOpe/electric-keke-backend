"""
The Module for user authentication related models
"""

import uuid
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

    def create_user(self, email=None, phone=None, password=None, **kwargs):
        """Function for creating user instance"""
        if email is None:
            raise TypeError('User must have an email address')
        if phone is None:
            raise TypeError('User must have a phone number')
        if password is None:
            raise TypeError('User must have a password')

        user = self.model(email=self.normalize_email(email),
                          phone=phone,
                          **kwargs,
                          )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, phone, password, **kwargs):
        """Super user function"""

        user = self.create_user(email, phone, password, **kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """The model for storing auth user details"""

    id = models.UUIDField(primary_key=True, 
                          default=uuid.uuid4, 
                          editable=False)
    email = models.EmailField(db_index=True, unique=True)
    phone = models.CharField(max_length=15, unique=True)
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
        return f'{self.id} {self.email}'
