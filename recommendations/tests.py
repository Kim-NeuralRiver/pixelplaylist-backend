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
from .services.openai_service import OpenAIServiceError
from recommendations.utils.slugify import slugify_title


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
        
    def test_email_and_username_login_comprehensive(self):
        # Test both email and username login paths work and return equivalent results
        # Test email login
        email_url = reverse('token_obtain_pair')
        email_data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        email_response = self.client.post(email_url, email_data, format='json')
        
        if email_response.status_code != status.HTTP_200_OK:
            self.fail(f"Email login failed: {email_response.data}")
        
        self.assertIn('access', email_response.data)
        self.assertIn('refresh', email_response.data)
        email_access_token = email_response.data['access']
        
        # Test username login
        username_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        username_response = self.client.post(email_url, username_data, format='json')
        
        if username_response.status_code != status.HTTP_200_OK:
            self.fail(f"Username login failed: {username_response.data}")
        
        self.assertIn('access', username_response.data)
        self.assertIn('refresh', username_response.data)
        username_access_token = username_response.data['access']
        
        # Verify both tokens work for protected endpoints
        profile_url = reverse('user-profile')
        
        # Test email token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {email_access_token}')
        email_profile_response = self.client.get(profile_url)
        if email_profile_response.status_code != status.HTTP_200_OK:
            self.fail(f"Profile access with email token failed: {email_profile_response.data}")
        
        # Clear previous creds
        self.client.credentials() 
        
        # Test username token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {username_access_token}')
        username_profile_response = self.client.get(profile_url) 
        if username_profile_response.status_code != status.HTTP_200_OK:
            self.fail(f"Profile access with username token failed: {username_profile_response.data}")
            
        # Both should return the same user data
        self.assertDictEqual(email_profile_response.data, username_profile_response.data)
        self.assertEqual(email_profile_response.data['username'], 'testuser')
        self.assertEqual(email_profile_response.data['email'], 'test@example.com')
        
    def test_login_edge_cases(self):
        # Test various edge cases for login auth
        
        url = reverse('token_obtain_pair')
        
        # Test case 1: Missing password
        response = self.client.post(url, {'email': 'test@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test case 2: Missing email/username
        response = self.client.post(url, {'password': 'testpassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test case 3: Empty email
        response = self.client.post(url, {'email': '', 'password': 'testpassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test case 4: Empty username
        response = self.client.post(url, {'username': '', 'password': 'testpassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test case 5: Both email and username provided (with username taking precedence)
        response = self.client.post(url, {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpassword123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
    def test_invalid_credentials(self):
        # Test login with invalid creds to check if they're rejected with 401 unauthorized
        # Fundamental security check
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@example.com',
            'username': 'testuser',  
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_invalid_email_format(self):
        # Test that ensures invalid email format returns 400 
        # More for me when testing than for core functionality
        url = reverse('token_obtain_pair')
        data = {
            'email': 'not-an-email',
            'password': 'testpassword123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
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
            'username': 'testuser', 
            'password': 'testpassword123'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        
        # More robust login val
        if login_response.status_code != status.HTTP_200_OK:
            self.fail(f"Login failed during protected endpoint test: {login_response.data}")
            
        if 'access' not in login_response.data:
            self.fail(f"Access token missing from login response: {login_response.data}")
                   
        token = login_response.data['access']
        if not token: 
            self.fail("Access token is empty after login")
        
        # try again *with* auth
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(url)
        
        if response.status_code != status.HTTP_200_OK:
            self.fail(f"Protected endpoint access failed with valid token, status: {response.status_code}: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        
    def test_password_change(self):
        # Test that users can change passwords when providing correct old password
        # Validates whole pass change flow, including verifying new creds
        
        # First, login to get token
        login_url = reverse('token_obtain_pair')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'username': 'testuser'  
        }
        login_response = self.client.post(login_url, login_data, format='json')
        
        # Robust login val
        if login_response.status_code != status.HTTP_200_OK:
            self.fail(f"Login failed during password change test: {login_response.data}")
            
        if 'access' not in login_response.data:
            self.fail(f"Access token missing from login response: {login_response.data}")
        
        token = login_response.data['access']
        if not token:
            self.fail("Access token is empty or None")
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try change pass
        url = reverse('change-password')
        data = {
            'old_password': 'testpassword123',
            'new_password1': 'newpassword456',
            'new_password2': 'newpassword456'
        }
        response = self.client.post(url, data, format='json')
        
        if response.status_code != status.HTTP_200_OK:
            self.fail(f"Password change failed: {response.data}")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify new pass works
        self.client.credentials() # clear creds
        login_data = {
            'email': 'test@example.com',
            'username': 'testuser',  
            'password': 'newpassword456'
        }
        response = self.client.post(login_url, login_data, format='json')
        
        if response.status_code != status.HTTP_200_OK:
            self.fail(f"Login with new password failed: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
    def test_password_change_incorrect_old(self):
        # Test pass changes are rejected if old pass is incorrect
        # Prevents unauth pass changes
        
        # First, login to get token
        login_url = reverse('token_obtain_pair')
        login_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'username': 'testuser'  
        }
        login_response = self.client.post(login_url, login_data, format='json')
        
        # more login val
        if login_response.status_code != status.HTTP_200_OK:
            self.fail(f"Login failed: {login_response.data}")
            
        if 'access' not in login_response.data:
            self.fail(f"Access token missing from login response: {login_response.data}")
        
        token = login_response.data['access']
        if not token:
            self.fail("Access token is empty or None")
        
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
                'platform': ['PC'],  
                'summary': 'This is a test game',
                'genres': ['Action', 'Adventure', 'RPG']  
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
                'platform': ['PC'],
                'summary': 'This is a test game',
                'genres': ['Action', 'Adventure', 'RPG']
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
        

class GenreListTests(APITestCase):
# Test genre listing functionality
    
    @patch('recommendations.views.fetch_igdb_genres')
    def test_genre_list_success(self, mock_fetch):
        # Test to check genre listing runs successfully
        # Runs a mock fetch to return sample genres
        
        mock_fetch.return_value = [
            {'id': 4, 'name': 'Fighting'},
            {'id': 5, 'name': 'Shooter'},
            {'id': 12, 'name': 'RPG'}
        ]
        
        # Make req
        url = reverse('genre-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Fighting')
        
    @patch('recommendations.views.fetch_igdb_genres')
    def test_genre_list_error(self, mock_fetch):
    # Mock genre fetch to raise and test genre list error handling
        mock_fetch.side_effect = GenreServiceError("Genre list service unavailable")
        
        # Make req
        url = reverse('genre-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)
        self.assertIn('error', response.data)
        
class PlaylistTests(APITestCase):
    # Test playlist functionality
    
    def setUp(self):
        # Create a test user 
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.client = APIClient()
        
        # login and retrieve token
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
        response = self.client.post(url, data, format='json')
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Sample playlist data 
        self.valid_playlist = {
            'name': 'TestPlaylist',
            'games': [
                {
                    'title': 'Test Game 1',
                    'cover_url': 'https://example.com/cover1.jpg',
                    'platform': ['PC'],
                    'summary': 'This is test game 1',
                    'genres': ['Action', 'Adventure'],
                    'price': {
                        'price': 19.99,
                        'store': 'Steam',
                        'currency': 'GBP'
                    }
                },
                {
                    'title': 'Test Game 2',
                    'cover_url': 'https://example.com/cover2.jpg',
                    'platform': ['PlayStation'],
                    'summary': 'This is test game 2',
                    'genres': ['RPG'],
                    'price': {
                        'price': 29.99,
                        'store': 'PSN',
                        'currency': 'GBP'
                    }
                } 
            ]
        }
        
    def test_create_playlist(self):
        
        # Test creating a new playlist
        # Verifies that both response format and data are actually stored in DB
        url = reverse('playlist-list-create')
        response = self.client.post(url, self.valid_playlist, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'TestPlaylist')  
        self.assertEqual(len(response.data['games']), 2)
        self.assertEqual(GamePlaylist.objects.count(), 1)
        
    def test_get_playlist(self):
        # Tests retrieving user playlist
        # Ensures users can see saved content when return to app
        # Create a playlist in DB first, then verify retrieval via API works
        
        # Playlist creation first
        GamePlaylist.objects.create(
            user=self.test_user,
            name='Existing Playlist',
            games=[{'title': 'Saved Game', 'platform': ['PC']}]
        )
        
        # The, get playlists
        url = reverse('playlist-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)#
        self.assertEqual(response.data[0]['name'], 'Existing Playlist')
        
    def test_playlist_user_isolation(self):
        # Test users may only see their own playlists
        # Test works by making playlists for multi users and verifying each only sees own data
        
        # Create another user and playlist
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword123'
        )
        GamePlaylist.objects.create(
            user=other_user,
            name="Other User's Playlist",
            games=[{'title': 'Other Game', 'platform': ['Xbox']}]
        )
        
        # Create a playlist for test user too
        GamePlaylist.objects.create(
            user=self.test_user,
            name='Test User Playlist',
            games=[{'title': 'My Game', 'platform': ['PC']}]
        )
        
        # Get playlist as test user
        url = reverse('playlist-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Should see only test user playlist
        self.assertEqual(response.data[0]['name'], 'Test User Playlist')
        
    def test_playlist_size_limit(self):
        # Tests playlist size
        # Validate that backend enforces constraints correctly to prevent resource overuse
        
        # Create playlist with too many games
        too_many_games = self.valid_playlist.copy()
        too_many_games['games'] = [
            {'title': f'Game {i}', 'platform': ['PC']} for i in range(8)
        ] 
        
        url = reverse('playlist-list-create')
        response = self.client.post(url, too_many_games, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
    def test_unauthorized_playlist_access(self):

        # Tests that unauthenticated users cannot access playlist endpoints.
        # The test tries both GET and POST requests to verify comprehensive protection.
        
        # Clear credentials
        self.client.credentials()
        
        # Try to access playlists without auth
        url = reverse('playlist-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to create playlist without auth
        response = self.client.post(url, self.valid_playlist, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
# Utility Tests

class UtilityTests(TestCase):
    
    # Tests utility functions used in the app to help it function
    # More can likely be added to these tests as needed, as of now we just have title slugification
    
    # First, test title slugification function (which converts game titles into url friendly slugs)
    # Tests common cases, special characters, and edge cases
    def test_slugify_title(self):
                
        # test w/ spaces
        self.assertEqual(slugify_title("Final Fantasy I"), "final-fantasy-i")
        
        # test with special chars
        self.assertEqual(slugify_title("Pokemon Mystery Dungeon: Blue Rescue Team"), "pokemon-mystery-dungeon-blue-rescue-team")
        
        # test with unicode characters 
        self.assertEqual(slugify_title("Pokémon Heart Gold"), "pokemon-heart-gold")
        
        # Test with multiple spaces and hyphens
        self.assertEqual(slugify_title("Star  Wars  -  The  Force  Unleashed"), "star-wars-the-force-unleashed")