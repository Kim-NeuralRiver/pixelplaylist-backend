from typing import List, Dict
from igdb_service import get_igdb_access_token
import requests

def fetch_igdb_genres() -> List[Dict]:
    access_token = get_igdb_access_token()
    
    url = "https://api.igdb.com/v4/genres"
    headers = {
        "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
        "Authorization": f"Bearer {access_token}",
    }
    
    query = "fields id, name; limit 100;"
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    
    return response.json()