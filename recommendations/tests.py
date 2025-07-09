from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import GamePlaylist
from .serializers import GamePlaylistSerializer, UserCreateSerializer
import json
from .services.igdb_service import IGDBServiceError
from .services.genre_service import GenreServiceError
from .services.price_service import PriceServiceError
from .services.openai_service import OpenAIServiceError

# Authentication Tests to test functionality:

class AuthenticationTests(APITestCase):
    
    def setUp(self):
        # Create test user first
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.client = APIClient()
        
    def test_user_registration(self):
        # Test if new users can register by sending POST req to user creation endpoint.
        # Should validate the user reg flow works correctly, and flag up any errors (e.g. user reg not working)
        url = reverse('user-create') 
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'name': 'Carmen Berzatto'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # One test user + one new user
        
    def test_email_login(self):
        # Verify users can login with email instead of username
        # This is useful because username function doesn't work right now, so this needs to work
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
    def test_username_login(self):
        # Tests username-based login
        # This is useful because username login doesn't work right now, and it needs to work.
        # This should confirm whether or not JWT token gen works for username auth
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
    def test_invalid_credentials(self):
        # Test login with invalid creds to check if they're rejected with 401 unauthorized
        # Fundamental security check
        url = reverse('token_obtain_pair')
        data = {
            'email': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_protected_endpoint_access(self):
        # Test accessing protected endpoint both with and without auth
        # Verifies endpoints that require auth are protected / reject unauthenticated requests but accept authenticated requests
        # Validates auth middleware works correctly
        
        # First = try without auth
        url = reverse('user-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Login and retrieve token
        login_url = reverse('token_obtain_pair')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access']
        
        # try again *with* auth
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        
    def test_password_change(self):
        # Test that users can change passwords when providing correct old password
        # Validates whole pass change flow, including verifying new creds
        
        # First, login to get token
        login_url = reverse('token_obtain_pair')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try change pass
        url = reverse('change-password')
        data = {
            'old_password': 'testpassword123',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify new pass works
        self.client.credentials() # clear creds
        login_data = {
            'email': 'test@example.com',
            'password': 'newpassword456'
        }
        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
    def test_password_change_incorrect_old(self):
        # Test pass changes are rejected if old pass is incorrect
        # Prevents unauth pass changes
        
        # First, login to get token
        login_url = reverse('token_obtain_pair')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try pass change with incorrect old pass
        url = reverse('change-password')
        data = {
            'old_password': 'wrongpassword',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    """End of Authentication Tests"""