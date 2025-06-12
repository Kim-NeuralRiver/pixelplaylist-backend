from typing import List, Dict
from .igdb_service import get_igdb_access_token, IGDBServiceError
import requests
import os
from django.core.cache import cache

# Define custom exception for Genre service failures
class GenreServiceError(RuntimeError):
    """Custom exception for errors specifically from the Genre fetching service."""
    pass

# Fetch a list of genres from IGDB API
# Return a list of dicts with genre ID and name

def fetch_igdb_genres() -> List[Dict]:
    cached_genres = cache.get("igdb_genres")
    if cached_genres:
        return cached_genres

    try:
        access_token = get_igdb_access_token()
    except IGDBServiceError as e:
        raise GenreServiceError(f"Failed to retrieve IGDB access token: {e}")
    
    url = "https://api.igdb.com/v4/genres"
    headers = {
        "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
        "Authorization": f"Bearer {access_token}",
    }
    
    query = "fields id, name; limit 100;"
    
    
    try:
        # Add a timeout to prevent hanging requests
        response = requests.post(url, headers=headers, data=query, timeout=5)
        response.raise_for_status()
        
        genres_data = response.json()
        
        cache.set("igdb_genres", genres_data, 60 * 60 * 24) # Cache for 24 hours (in seconds)
        
        return genres_data
    except requests.exceptions.Timeout:
        raise GenreServiceError("IGDB genres query timed out.")
    except requests.exceptions.RequestException as e:
        raise GenreServiceError(f"Network error during IGDB genres query: {e}")
    except ValueError as e:
        raise GenreServiceError(f"Failed to parse JSON response during IGDB genres query: {e}")
    except Exception as e:
        raise GenreServiceError(f"An unexpected error occurred during IGDB genres query: {e}")
