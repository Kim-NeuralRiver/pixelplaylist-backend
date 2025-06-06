import os
import requests
from typing import List, Dict

# Auth with Twitch API to get access token for IGDB requests
# For debugging: raises runtime error is token cannot be retrieved

def get_igdb_access_token() -> str:
    client_id = os.getenv('TWITCH_CLIENT_ID') # Lazy loading for efficiency and to prevent errors
    client_secret = os.getenv('TWITCH_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise RuntimeError("Twitch Client ID or Secret not set in environment variables.")

    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        'client_id': client_id,  
        'client_secret': client_secret,  
        'grant_type': 'client_credentials'
    }

    response = requests.post(url, data=payload)
    response.raise_for_status()

    access_token = response.json().get('access_token')
    if not access_token:
        raise RuntimeError("Failed to retrieve IGDB access token")

    return access_token


# Query IGDB for games matching specified criteria (genres and platform)
# Return simplified game data dict

def query_igdb_games(genre_ids: List[int], platform_id: List[int], limit=10) -> List[Dict]: # Increase limit AFTER testing

    access_token = get_igdb_access_token()

    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
        'Authorization': f'Bearer {access_token}'
    }
    
    # Construct IGDB query: filter by genres and platform, sort by popularity, get important fields
    
    query = f"""
    fields name, cover.image_id, platforms.name, summary, genres.name;
    where genres = ({', '.join(map(str, genre_ids))}) & platforms = ({str(platform_id)}); 
    sort popularity desc;
    limit {limit};
    """
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    
    games = response.json()
    if not games:
        raise RuntimeError("No games found for the specified criteria") # in case of odd requests or bugs
    
    # Format and return simplified game data
    return format_igdb_response(games)

#Take raw API response and format into frontend friendly dict format
def format_igdb_response(games: List[Dict]) -> List[Dict]:
    formatted_games = []
    for game in games:
        cover_url = (
            f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game['cover']['image_id']}.jpg"
            if game.get('cover') else None
        )
        
        formatted_games.append({
            "title": game['name'],
            "cover_url": cover_url,
            "platform": [p['name'] for p in game.get('platform', [])],
            "summary": game.get('summary', ''),
            "genres": [g['name'] for g in game.get('genres', [])],
        })
        
    return formatted_games
        
        