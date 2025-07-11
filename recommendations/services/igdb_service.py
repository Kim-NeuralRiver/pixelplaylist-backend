import os
import requests
from typing import List, Dict
from django.core.cache import cache

# Define custom exception for IGDB service errors
class IGDBServiceError(RuntimeError):
    """Custom exception for IGDB service errors, can be used to handle specific IGDB issues in views or other services."""
    pass

# Auth with Twitch API to get access token for IGDB requests
# For debugging: raises runtime error is token cannot be retrieved

def get_igdb_access_token() -> str:
    
    # Try to get token from cache first to reduce API calls
    cached_token = cache.get("igdb_access_token")
    if cached_token:
        return cached_token
    
    client_id = os.getenv('TWITCH_CLIENT_ID') # Lazy loading for efficiency and to prevent errors
    client_secret = os.getenv('TWITCH_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise IGDBServiceError("Twitch Client ID or Secret not set in environment variables.")

    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        'client_id': client_id,  
        'client_secret': client_secret,  
        'grant_type': 'client_credentials'
    }
    
    try: #Add timeout to prevent hanging requests
        response = requests.post(url, data=payload, timeout=10)  # 10 seconds timeout
        response.raise_for_status()  # Raise an error for bad responses
        
        data = response.json()
        access_token = data.get('access_token')
        expires_in = data.get('expires_in', 3600)  # Default to 1 hour if not specified
        
        if not access_token:
            raise IGDBServiceError("Failed to retrieve IGDB access token from Twitch API.")
        
        cache.set("igdb_access_token", access_token, expires_in - 300)  # Cache for 5 mins less than expiry

        return access_token
    except requests.exceptions.Timeout:
        raise IGDBServiceError("IGDB access token request timed out.")
    except requests.exceptions.RequestException as e:
        raise IGDBServiceError(f"Network error during IGDB access token retrieval: {e}")
    except ValueError as e:
        raise IGDBServiceError(f"Failed to parse JSON response during IGDB access token retrieval: {e}")
    except Exception as e:
        raise IGDBServiceError(f"An unexpected error occurred during IGDB access token retrieval: {e}")


# Query IGDB for games matching specified criteria (genres and platform)
# Return simplified game data dict

# Query IGDB for games matching specified criteria (genres and platform)
# Return simplified game data dict

def query_igdb_games(genre_ids: List[int], platform_id: List[int], limit=10) -> List[Dict]: # Increase limit AFTER testing

    try:
        access_token = get_igdb_access_token()
    except IGDBServiceError as e:
        raise IGDBServiceError(f"Failed to get IGDB access token: {e}")

    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
        'Authorization': f'Bearer {access_token}'
    }
    
    # Construct IGDB query: filter by genres and platform, sort by popularity, get important fields
    # Fixed platform_id handling to properly format the list
    genre_list = ', '.join(map(str, genre_ids))
    platform_list = ', '.join(map(str, platform_id))
    
    # Only include certain game categories, to avoid irrelevant results
    allowed_categories = [0, 3, 4, 8, 9 , 10, 11, 12] # main_game, bundle, standalone_expansion, remake, remaster, expanded_game, port, fork
    category_filter = ' | '.join([f'category = {category}' for category in allowed_categories])
    
    query = f"""
    fields name, cover.image_id, platforms.name, summary, genres.name;
    where genres = ({genre_list}) & platforms = ({platform_list}) & ({category_filter});
    sort popularity desc; 
    limit {limit}; 
    """
    
    try:
        response = requests.post(url, headers=headers, data=query, timeout=10)
        response.raise_for_status()
    
        games = response.json()
        if not games:
            return []  
        
    # Format and return simplified game data
        return format_igdb_response(games)
    except requests.exceptions.Timeout:
        raise IGDBServiceError("IGDB games query timed out.")
    except requests.exceptions.RequestException as e:
        raise IGDBServiceError(f"Network error during IGDB games query: {e}")
    except ValueError as e:
        raise IGDBServiceError(f"Failed to parse JSON response from IGDB games query: {e}")
    except Exception as e:
        raise IGDBServiceError(f"An unexpected error occurred during IGDB games query: {e}")
    
#Take raw API response and format into frontend friendly dict format
def format_igdb_response(games: List[Dict]) -> List[Dict]:
    formatted_games = []
    for game in games:
        cover_url = (
            f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game['cover']['image_id']}.jpg"
            if game.get('cover') and game['cover'].get('image_id') else None
        )
        
        formatted_games.append({
            "igdb_id": game.get('id'), # Include IGDB ID for future reference/linking
            "title": game.get('name', 'Unknown Title'),  # This should work with price_service
            "cover_url": cover_url,
            "platform": [p.get('name') for p in game.get('platforms', []) if p.get('name')], 
            "summary": game.get('summary', ''),
            "genres": [g.get('name') for g in game.get('genres', []) if g.get('name')],
            "release_date": game.get('first_release_date'), # Added for potential future use
            "rating": game.get('aggregated_rating'), # Added for potential future use
        })
        
    return formatted_games