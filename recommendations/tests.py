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
from .services.price_service import ITADServiceError
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
    
# Game recommendation tests to test functionality using mock external API calls:

class GameRecommendationTests(APITestCase):
    
    def setUp(self):
        self.url = reverse('game-recommendations')
        self.valid_input = {
            'genres': [4, 5, 12],
            'platform': [6],
            'budget': 50.0
        }
        
    @patch('recommendations.views.query_igdb_games')
    def test_recommendation_no_games_found(self, mock_query):
        # Test how system reacts when no games match user's criteria
        # Helps handling edge cases (which are somewhat hard to replicate irl)
        # Uses mock to simulate empty api results without making actual API calls
        
        # Mock the query_igdb_games to return empty list
        mock_query.return_value = []
        
        # Make req
        response = self.client.post(self.url, self.valid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('No games found', response.data['message'])
        
        
    @patch('recommendations.views.query_igdb_games')
    @patch('recommendations.views.get_game_price')
    @patch('recommendations.views.get_game_id')
    @patch('recommendations.views.generate_game_blurb')
    def test_successful_recommendation(self, mock_blurb, mock_get_id, mock_get_price, mock_query):
        # Test complete rec pipeline when all ext APIS work correctly
        # This 'best / normal case' test ensures core functionality works under normal expected conditions
        # Need to test full integration flow from search to to look/up to blurb gen
        # Tests all use multiple patches to mock all ext API calls, making them fast and reliable

        # Mock IGDB query to return sample games
        mock_query.return_value = [
            {
                'igdb_id': 123,
                'title': 'Test Game 1',
                'cover_url': 'https://example.com/cover1.jpg',
                'platform': [6],
                'summary': 'This is a test game',
                'genres': [3, 4, 5]
            }
        ]
        
        # Mock ITAD responses
        mock_get_id.return_value = 'testgame1'
        mock_get_price.return_value = [
            {
                'price': {'amount': 19.99},
                'shop': {'name': 'Steam'},
                'cut': 50,
                'url': 'https://store.steampowered.com/app/123'
            }
        ]
        
        # Mock OpenAI blurb
        mock_blurb.return_value = "This game is amazing! And this blurb is totally not a complete repetition of the previous blurb!"
        
        # Make request
        response = self.client.post(self.url, self.valid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Game 1')
        self.assertEqual(response.data[0]['blurb'], "This game is amazing! And this blurb is totally not a complete repetition of the previous blurb!")
        self.assertEqual(response.data[0]['price']['price'], 19.99)
        
    @patch('recommendations.views.query_igdb_games')
    def test_igdb_service_error(self, mock_query):
        # Test how system handles IGDB API failures
        # Needs to handle failure gracefully and w/ proper error messages.
        # Verify we return proper error messages and don't just crash / silently fail
        
        # Mock IGDB query to raise error
        mock_query.side_effect = IGDBServiceError("IGDB API unavailable")
        
        # Make request
        response = self.client.post(self.url, self.valid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)
        self.assertIn('error', response.data)
        
        
    @patch('recommendations.views.query_igdb_games')
    @patch('recommendations.views.get_game_id')
    def test_itad_service_error_handled_gracefully(self, mock_get_id, mock_query):
        # Test price l/u failure handling, ensures that price l/u failures don't crash the whole rec system
        # I.e. tests graceful degradation, the ability to return partial results when some components return none#
        
        # Mock IGDB query to return sample game
        mock_query.return_value = [
            {
                'igdb_id': 123,
                'title': 'Test Game 1',
                'platform': [6],
                'summary': 'This is a test game',
                'genres': [3, 4, 5]
            }
        ]
        
        # Mock ITAD to fail
        mock_get_id.side_effect = ITADServiceError("ITAD API unavailable")
        
        # Make request - should still return game but with price note
        response = self.client.post(self.url, self.valid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn('price_note', response.data[0])
        
    def test_invalid_input_validation(self):
        # Tests how we handle invalid input data (e.g. negative budget value, or above maximum) and ensures they're properly rejected
        # Ensures data integrity 
        # Multiple tests / validation scenarios to ensure comprehensive validation 
        
        # Test with negative budget
        invalid_input = self.valid_input.copy()
        invalid_input['budget'] = -10.0
        response = self.client.post(self.url, invalid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test with empty genres list
        invalid_input = self.valid_input.copy()
        invalid_input['genres'] = []
        response = self.client.post(self.url, invalid_input, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)