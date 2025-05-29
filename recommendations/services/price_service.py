import os
import requests
from typing import Optional, Dict
from recommendations.utils.slugify import slugify_title


def get_game_id(game_title: str) -> Optional[str]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise RuntimeError("ITAD_API_KEY not set in environment variables")

    url = f"{base_url}/games/search/v1" # <- GET

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

            if "data" in data and isinstance(data["data"], list) and data["data"]:
                return data["data"][0].get("plain") # <-- this is where I return game id
            
        except requests.HTTPError as e:
            print(f"[ITAD ERROR] Title lookup failed for '{attempt}': {e}")
            continue

    return None


#this needs to take the returned game id from ^
def get_game_price(game_id: str) -> Optional[Dict]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise RuntimeError("ITAD_API_KEY not set in environment variables")

    url = f"{base_url}/games/prices/v3" # <- POST

    headers = {
        "Content-Type": "application/json"
    }
    
    json_body = {
        "plains": [game_id] # <-- request body
    }
    
    params = {
        "key": api_key,
        "country": "GB"
    }
    
    try: # try to get price
        response = requests.post(url, params=params, headers=headers, json=json_body) #request body goes in here
        response.raise_for_status()
        data = response.json()
        
        deals = data.get("data", {}).get(game_id, {}).get("list", [])
        if deals:
            return deals[0].get("price")
        else:
            print(f"[ITAD Error]: No deals found for game: {game_id}")
            return None
        
    except requests.HTTPError as e: 
        print(f"[ITAD Error]: Failed to fetch price for game '{game_id}': {e}")
        return None
        

"""  Maybe insert a second GET request below for further game data """

 
    # if isinstance(data, dict) and "data" in data:
    #     for item in data["data"]:
    #         if item.get("id") == game_id:
    #             return item

   # return None
   
   # ^-- Don't think I need to above anymore, keeping just in case
   
