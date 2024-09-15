"""
Testing for Bookings endpoints
"""
# pylint: disable=no-member

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User
from .models import Booking

class BookingTests(APITestCase):
    def setUp(self):
        """
        Create multiple users with different roles (Rider, User, Admin) and authenticate.
        """
        # URLs
        self.get_avalailable_riders_url = reverse('riders')
        self.new_booking_url = reverse('booking-create')
        self.get_all_bookings_url = reverse('booking-list')

        # Create User roles
        self.user = User.objects.create_user(
            fullname='Jane Doe',
            email='jane@example.com',
            phone='09087654321',
            password='password123',
            address='456 Secondary St',
            state_of_residence='Lagos',
            role='User',
            is_active=True
        )
        self.rider = User.objects.create_user(
            fullname='John Rider',
            email='rider@example.com',
            phone='09087654782',
            password='riderpassword',
            address='456 Secondary St',
            state_of_residence='Lagos',
            role='Rider',
            is_active=True
        )
        self.admin = User.objects.create_user(
            fullname='Admin Jane',
            email='admin@example.com',
            phone='08087654321',
            password='adminpassword',
            address='456 Secondary St',
            state_of_residence='Lagos',
            role='Admin',
            is_active=True
        )

        # Create a booking instance for testing status update
        self.booking = Booking.objects.create(
            user=self.user,
            rider=self.rider,
            booking_type='ride',
            origin='123 Street',
            destination='456 Avenue',
            price=1500.00
        )

        # URL for booking status update with a booking ID
        self.update_booking_status_url = reverse('booking-status-update', kwargs={'pk': self.booking.id})

    def authenticate_user(self):
        """Helper method to authenticate a User."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.user).access_token}')

    def authenticate_rider(self):
        """Helper method to authenticate a Rider."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.rider).access_token}')

    def authenticate_admin(self):
        """Helper method to authenticate an Admin."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.admin).access_token}')

    def test_list_available_riders(self):
        """
        Test listing all available riders (as a User).
        """
        self.authenticate_user()  # Authenticate as User
        response = self.client.get(self.get_avalailable_riders_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_booking_as_user(self):
        """
        Test creating a booking (as a User).
        """
        self.authenticate_user()
        data = {
            'rider': self.rider.email,  # Using the rider's email
            'booking_type': 'ride',
            'origin': '123 Street',
            'destination': '456 Avenue',
            'price': 1500.00
        }
        response = self.client.post(self.new_booking_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')

    def test_create_booking_as_rider(self):
        """
        Test that a Rider cannot create a booking.
        """
        self.authenticate_rider()
        data = {
            'rider': self.rider.email,  # Using the rider's email
            'booking_type': 'ride',
            'origin': '123 Street',
            'destination': '456 Avenue',
            'price': 1500.00
        }
        response = self.client.post(self.new_booking_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # Forbidden for Riders

    def test_create_booking_with_invalid_data(self):
        """
        Test creating a booking with invalid data (e.g., missing required fields).
        """
        self.authenticate_user()
        data = {
            'rider': '',  # Missing rider email
            'booking_type': 'ride',
            'origin': '',
            'destination': '456 Avenue',
            'price': 1500.00
        }
        response = self.client.post(self.new_booking_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rider', response.data)
        self.assertIn('origin', response.data)  # Missing fields should raise validation errors

    def test_list_bookings_as_user(self):
        """
        Test getting the list of bookings for the logged-in User.
        """
        self.authenticate_user()  # Authenticate as User
        response = self.client.get(self.get_all_bookings_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # One booking should be available for this user

    def test_list_bookings_as_rider(self):
        """
        Test getting the list of bookings for the logged-in Rider.
        """
        self.authenticate_rider()  # Authenticate as Rider
        response = self.client.get(self.get_all_bookings_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # One booking should be available for this rider

    def test_list_bookings_with_invalid_user(self):
        """
        Test list bookings with an invalid user role.
        """
        self.client.credentials()  # No token provided
        response = self.client.get(self.get_all_bookings_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)  # Unauthenticated access

    def test_update_booking_status_by_user(self):
        """
        Test updating a booking's status by the User.
        """
        self.authenticate_user()  # Authenticate as User

        url = reverse('booking-status-update', args=[self.booking.id])
        data = {'status': 'cancelled'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_update_booking_status_by_rider(self):
        """
        Test updating a booking's status by the Rider.
        """
        self.authenticate_rider()  # Authenticate as Rider

        url = reverse('booking-status-update', args=[self.booking.id])
        data = {'status': 'in_progress'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')

    def test_update_booking_status_with_invalid_booking(self):
        """
        Test updating a booking's status with an invalid booking ID.
        """
        self.authenticate_user()  # Authenticate as User

        url = reverse('booking-status-update', args=[9999])  # Invalid booking ID
        data = {'status': 'cancelled'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Booking not found

    def test_unauthenticated_access(self):
        """
        Test accessing endpoints without authentication.
        """
        self.client.credentials()  # Remove any credentials

        response = self.client.get(self.get_all_bookings_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
