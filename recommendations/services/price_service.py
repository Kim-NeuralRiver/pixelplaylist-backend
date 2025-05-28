import os
import requests
from typing import Optional, Dict
from recommendations.utils.slugify import slugify_title


def get_game_id(game_title: str) -> Optional[str]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise RuntimeError("ITAD_API_KEY not set in environment variables")

    url = f"{base_url}/games/search/v1"

    for attempt in [game_title, slugify_title(game_title)]:
        params = {
            "key": api_key,
            "title": attempt,
            "results": 1
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and data:
                return data[0].get("id")
        except requests.HTTPError as e:
            print(f"[ITAD ERROR] Title lookup failed for '{attempt}': {e}")
            continue

    #return game id here
    return None


#this needs to take the returned game id from ^
def get_game_price(game_id: str) -> Optional[Dict]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise RuntimeError("ITAD_API_KEY not set in environment variables")

    url = f"{base_url}/games/prices/v3"
    params = {
        "key": api_key,
        "country": "GB"
    }

    headers = {
        "Content-Type": "application/json"
    }

    #need to add a request body like 
    #[
    # "018d937f-1382-7004-b65b-e6adfce11377" <-- this is the game id from the function above
    #]

    response = requests.post(url, params=params, headers=headers, json=[game_id]) #request body goes in here
    response.raise_for_status()

    data = response.json()

    #we want data["deals"][0]["price"] <-- something like this

    if isinstance(data, dict) and "data" in data:
        for item in data["data"]:
            if item.get("id") == game_id:
                return item

    return None
