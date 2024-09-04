"""Custom Permissions for different users"""

from rest_framework.permissions import BasePermission

class IsUser(BasePermission):
    """Custom permission to only allow Users to access certain views."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'User'


class IsRider(BasePermission):
    """Custom permission to only allow Riders to access certain views."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Rider'
