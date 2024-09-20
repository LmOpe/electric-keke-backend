from datetime import datetime, timedelta

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.timezone import now

from bookings.models import Booking

User = get_user_model()

class TestUserListView(APITestCase):

    def setUp(self):
        self.url = reverse('user-list')  # Assuming 'user-list' is the URL name
        self.admin_user = User.objects.create_superuser(
            fullname='Admin User', email='admin@example.com', password='adminpass', phone=2349026728365)
        self.normal_user = User.objects.create_user(
            fullname='Normal User', email='user@example.com', password='userpass', role='User', is_active=True, phone=2349096728365)
        
        self.normal_user.created_at = now() - timedelta(days=1)
        self.normal_user.save()
    
    def authenticate_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.admin_user).access_token}')
    
    def test_admin_can_view_user_list(self):
        """Admin should be able to get the list of users"""
        self.authenticate_admin()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Check if two users are returned

    def test_user_cannot_view_user_list(self):
        """Normal users should not have access to the user list"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.normal_user).access_token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthenticated_cannot_view_user_list(self):
        """Unauthenticated users should not have access"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_can_filter_by_status(self):
        """Admin should be able to filter users by status"""
        self.authenticate_admin()
        response = self.client.get(self.url, {'status': 'active'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # All users are active by default in setup
    
    def test_admin_can_filter_by_signup_date(self):
        """Admin should be able to filter users by signup date"""
        self.authenticate_admin()
        response = self.client.get(self.url, {'signup_date': self.normal_user.created_at.strftime('%d/%m/%Y')})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only 1 user should match

class DashboardOverviewTestCase(APITestCase):
    def setUp(self):
        # Create admin, rider, and normal user
        self.admin_user = User.objects.create_superuser(
            fullname='Admin User',
            email='admin@example.com',
            phone=2349026728378,
            password='adminpass',
        )

        self.normal_user = User.objects.create_user(
            fullname='Normal User',
            email='user@example.com',
            phone=2349026728678,
            password='userpass',
            role='User',
            is_active=True,
        )

        self.rider = User.objects.create_user(
            fullname='Rider User',
            email='rider@example.com',
            phone=2349056728378,
            password='riderpass',
            role='Rider',
            is_active=True,
        )

        # Create ride and delivery bookings
        self.ride_booking = Booking.objects.create(
            user=self.normal_user,
            rider=self.rider,
            booking_type='ride',
            origin='123 Street',
            destination='456 Avenue',
            price=1500.00,
        )

        self.delivery_booking = Booking.objects.create(
            user=self.normal_user,
            rider=self.rider,
            booking_type='delivery',
            origin='789 Street',
            destination='321 Avenue',
            price=2000.00
                            )

        # URL for dashboard overview
        self.dashboard_overview_url = reverse('dashboard-overview')

  
    def authenticate_admin(self):
        """Helper method to authenticate the admin user."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.admin_user).access_token}')

    def test_dashboard_overview_admin_success(self):
        """Test that admin can successfully retrieve dashboard overview data."""
        self.authenticate_admin()
        response = self.client.get(self.dashboard_overview_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total_users'], 3)
        self.assertEqual(data['total_active_users'], 3)
        self.assertEqual(data['total_inactive_users'], 0)
        self.assertEqual(data['total_rides'], 1)
        self.assertEqual(data['total_deliveries'], 1)
        self.assertEqual(data['total_ride_earnings'], 1500.0)
        self.assertEqual(data['total_delivery_earnings'], 2000.0)

    def test_dashboard_overview_unauthorized(self):
        """Test that non-admin users cannot access dashboard overview."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.normal_user).access_token}')
        response = self.client.get(self.dashboard_overview_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_dashboard_overview_without_authentication(self):
        """Test that unauthenticated requests are denied access."""
        response = self.client.get(self.dashboard_overview_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class TestEarningsListView(APITestCase):
    def setUp(self):
        # URLs
        self.url = reverse('earnings-list')  # Assuming 'earnings-list' is the URL name

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            fullname='Admin User', email='admin@example.com', password='adminpass', phone=2349026728365)

        # Create normal user and rider
        self.normal_user = User.objects.create_user(
            fullname='Normal User', email='user@example.com', password='userpass', phone=2349096728365, role='User', is_active=True)
        
        self.rider_user = User.objects.create_user(
            fullname='Rider User', email='rider@example.com', password='riderpass', phone=2349036728365, role='Rider', is_active=True)
        
        # Create a booking for ride
        self.ride_booking = Booking.objects.create(
            user=self.normal_user,
            rider=self.rider_user,
            booking_type='ride',
            price=1000,
            created_at=now()
        )
        
        # Create a booking for delivery
        self.delivery_booking = Booking.objects.create(
            user=self.normal_user,
            rider=self.rider_user,
            booking_type='delivery',
            price=2000,
        )

        self.delivery_booking.created_at = now() - timedelta(days=1)
        self.delivery_booking.save()

    def authenticate_admin(self):
        """Helper method to authenticate the admin user."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.admin_user).access_token}')

    def test_admin_can_view_earnings(self):
        """Test that an admin can view all earnings."""
        self.authenticate_admin()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)  # Check earnings data is returned
    
    def test_filter_by_type(self):
        """Test admin can filter earnings by booking type (ride/delivery)."""
        self.authenticate_admin()
        response = self.client.get(self.url, {'type': 'ride'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only one booking of type 'ride'

        # Test filtering by delivery
        response = self.client.get(self.url, {'type': 'delivery'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only one booking of type 'delivery'

    def test_filter_by_date(self):
        """Test admin can filter earnings by specific date."""
        self.authenticate_admin()
        date_str = self.ride_booking.created_at.strftime('%d/%m/%Y')
        response = self.client.get(self.url, {'date': date_str})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only one booking on this specific date

    def test_filter_by_date_range(self):
        """Test admin can filter earnings by a date range."""
        self.authenticate_admin()
        date_from = (now() - timedelta(days=2)).strftime('%d/%m/%Y')
        date_to = now().strftime('%d/%m/%Y')

        response = self.client.get(self.url, {'date_from': date_from, 'date_to': date_to})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Both bookings should be within the range
    
    def test_invalid_date_format(self):
        """Test that an invalid date format returns a 400 error."""
        self.authenticate_admin()
        response = self.client.get(self.url, {'date': 'invalid-date'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthorized_user_cannot_access(self):
        """Test that unauthorized users cannot access the earnings list."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)