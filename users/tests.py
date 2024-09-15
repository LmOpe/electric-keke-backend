"""Testing the views with"""

# pylint: disable=no-member
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from unittest.mock import patch
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP

class UserAuthenticationTests(APITestCase):
   
    def setUp(self):
        self.register_url = reverse('register_user')
        self.activate_user_url = reverse('activate_user')
        self.request_new_otp_url = reverse('request_new_otp')
        self.token_obtain_url = reverse('token_obtain_pair')
        self.token_refresh_url = reverse('token_refresh')
        self.reset_password_url = reverse('reset_password')
        self.delete_account_url = reverse("delete_account")
        self.get_auth_user_url = reverse("auth_user")
        self.logout_url = reverse("logout")

        self.user_data = {
            'fullname': 'John Doe',
            'email': 'john@example.com',
            'phone': '09012345678',
            'password': 'password123',
            're_password': 'password123',
            'address': '123 Main St',
            'state_of_residence': 'Kwara',
            'role': 'User',
            'message_type': 'email'
        }

        self.user = User.objects.create_user(
            fullname='Jane Doe',
            email='jane@example.com',
            phone='09087654321',
            password='password123',
            address='456 Secondary St',
            state_of_residence='Lagos',
            role='User'
        )
        self.user.is_active = True
        self.user.save()

        # JWT token for authenticated requests
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def authenticate_user(self):
        """Helper method to set the authorization header for requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_register_user_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(OTP.objects.filter(user__email=self.user_data['email']).exists())

    def test_register_user_password_mismatch(self):
        self.user_data['re_password'] = 'differentpassword'
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_activate_user_invalid_otp(self):
        self.user.is_active = False
        self.user.save()
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() - timedelta(minutes=5))
        response = self.client.post(self.activate_user_url, {'id': self.user.id, 'otp': '12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_activate_user_already_active(self):
        """
        Test activating a user who is already active.
        """
        self.user.is_active = True
        self.user.save()

        response = self.client.post(self.activate_user_url, {'id': self.user.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'User is already active.')

    def test_activate_user_success(self):
        self.user.is_active = False
        self.user.save()
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() + timedelta(minutes=5))
        response = self.client.post(self.activate_user_url, {'id': self.user.id, 'otp': '12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_request_new_otp_success_email(self):
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() - timedelta(minutes=5))
        response = self.client.post(self.request_new_otp_url, {'username': self.user.email, 'message_type': 'email'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=self.user).exists())

    def test_request_new_otp_user_not_found(self):
        response = self.client.post(self.request_new_otp_url, {'username': 'nonexistent@example.com', 'message_type': 'email'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_otp_success(self):
        """
        Test successfully verifying the OTP.
        """
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() + timedelta(minutes=5))
        response = self.client.post(self.otp_verification_url, {'id': self.user.id, 'otp': '12345'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'OTP verified successfully.')

    def test_verify_otp_invalid(self):
        """
        Test verification with an invalid OTP.
        """
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() + timedelta(minutes=5))
        response = self.client.post(self.otp_verification_url, {'id': self.user.id, 'otp': '54321'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired OTP.')

    def test_verify_otp_expired(self):
        """
        Test verification with an expired OTP.
        """
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() - timedelta(minutes=1))  # Expired OTP
        response = self.client.post(self.otp_verification_url, {'id': self.user.id, 'otp': '12345'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired OTP.')

    def test_verify_otp_user_not_found(self):
        """
        Test verification with a non-existing user.
        """
        response = self.client.post(self.otp_verification_url, {'id': 999, 'otp': '12345'}, format='json')  # Non-existing user

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'User or OTP not found.')

    def test_custom_token_obtain_pair_success(self):
        response = self.client.post(self.token_obtain_url, {'username': self.user.email, 'password': 'password123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_custom_token_obtain_pair_invalid_credentials(self):
        response = self.client.post(self.token_obtain_url, {'username': self.user.phone, 'password': 'wrongpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_custom_token_refresh_success(self):
        response = self.client.post(self.token_obtain_url, {'username': self.user.email, 'password': 'password123'}, format='json')
        refresh_token = response.data['refresh']
        response = self.client.post(self.token_refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_custom_token_refresh_invalid_token(self):
        response = self.client.post(self.token_refresh_url, {'refresh': 'invalidtoken'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reset_password_success(self):
        response = self.client.post(self.reset_password_url, {'username': self.user.email, 'password': 'newpassword123', 're_password': 'newpassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

    def test_reset_password_mismatch(self):
        response = self.client.post(self.reset_password_url, {'username': self.user.email, 'password': 'newpassword123', 're_password': 'differentpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_user_not_found(self):
        response = self.client.post(self.reset_password_url, {'username': 'nonexistent@example.com', 'password': 'newpassword123', 're_password': 'newpassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('users.views.send_otp_email')
    def test_register_user_and_send_otp_email(self, mock_send_otp_email):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(OTP.objects.filter(user__email=self.user_data['email']).exists())
        self.assertTrue(mock_send_otp_email.called)

    def test_activate_user_with_correct_otp(self):
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() + timedelta(minutes=5))
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.activate_user_url, {'id': self.user.id, 'otp': '12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_activate_user_with_incorrect_otp(self):
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() + timedelta(minutes=5))
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.activate_user_url, {'id': self.user.id, 'otp': '54321'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_activate_user_with_expired_otp(self):
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() - timedelta(minutes=5))
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.activate_user_url, {'id': self.user.id, 'otp': '12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    @patch('users.views.send_otp_email')
    def test_request_new_otp_and_send_email(self, mock_send_otp_email):
        OTP.objects.create(user=self.user, otp='12345', expires_at=timezone.now() - timedelta(minutes=5))
        response = self.client.post(self.request_new_otp_url, {'username': self.user.email, 'message_type': 'email'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=self.user).exists())
        self.assertTrue(mock_send_otp_email.called)

    
    def test_get_authenticated_user(self):
        """Test retrieving the authenticated user's information."""
        self.authenticate_user()
        response = self.client.get(self.get_auth_user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['fullname'], self.user.fullname)

    def test_logout_success(self):
        """Test that a user can log out and their tokens are blacklisted."""
        self.authenticate_user()
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertIn('Successfully logged out', response.data['detail'])

    def test_delete_account_success(self):
        """Test that a user can delete their account."""
        self.authenticate_user()
        response = self.client.delete(self.delete_account_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())