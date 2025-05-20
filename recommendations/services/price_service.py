import os
import requests
from typing import Optional, Dict


def get_game_id(game_title: str) -> Optional[str]: # Uses IsThereAnyDeal's v3 search endpoint to retrieve the game UUID by title.

    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"

    if not api_key:
        raise RuntimeError("IsThereAnyDeal API key not found in environment variables")

    url = f"{base_url}/games/search/v1"
    headers = {
        "Authorization": f"key={api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "title": game_title
    }

    response = requests.post(url, headers=headers, json=payload)  # Changed to POST 

    data = response.json()

    # Return a list of game entries
    if isinstance(data, list) and data:
        return data[0].get("id")  # UUID string
    return None


def get_game_price(game_id: str) -> Optional[Dict]: # Uses IsThereAnyDeal's v3 pricing endpoint to fetch price and discount info for a given game UUID.

    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"

    if not api_key:
        raise RuntimeError("IsThereAnyDeal API key not found in environment variables")

    url = f"{base_url}/games/prices/v3"
    headers = {
        "Authorization": f"key={api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "country": "GB"  # Customize as needed
    }
    payload = [game_id]  # Must be a list of IDs

    response = requests.post(url, headers=headers, params=params, json=payload)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        for game in data:
            if game.get("id") == game_id:
                return game

    return None
