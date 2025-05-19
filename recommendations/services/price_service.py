# IsThereAnyDeal budget tracking service file 

import os
import requests
from typing import Optional, Dict

def get_plain_id(game_title: str) -> Optional[str]: # Function to get plain ID for game title, using ITAD's search endpoint
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    
    if not api_key:
        raise RuntimeError("ITAD API key not found in environment variables")
    
    url = f"{base_url}/lookup/id/title/v1"
    params = {
        "key": api_key,
        "q": game_title,
        "limit": 1, # Change later after testing
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    results = response.json().get("data", {}).get("results", [])
    if results:
        return results[0].get("plain")
    return None

# Use ITAD price endpoint to fetch price & discount info for queried game

def get_game_price(plain_id: str) -> Optional[Dict]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    
    if not api_key:
        raise RuntimeError("ITAD API key not found in environment variables")
    
    url = f"{base_url}/games/prices/v3"
    params = {
        "key": api_key,
        "plains": plain_id,
        "region": "uk",  
        "country": "GB"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json().get("data", {})
    return data.get(plain_id)