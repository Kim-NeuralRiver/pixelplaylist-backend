import os
import requests
from typing import Optional, List, Dict
from recommendations.utils.slugify import slugify_title

# Define custom exception for ITAD service failures
class ITADServiceError(RuntimeError):
    """Custom exception for errors specifically from the IsThereAnyDeal (ITAD) service."""
    pass

def get_game_id(game_title: str) -> Optional[str]:
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise ITADServiceError("ITAD_API_KEY not set in environment variables.")

    url = f"{base_url}/games/search/v1"
    
    # Try both original title and slugified version
    attempts = [game_title, slugify_title(game_title)]
    last_error = None
    
    for i, attempt in enumerate(attempts):
        params = {
            "key": api_key,
            "title": attempt,
            "results": 1 
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Debug logging to understand response structure
            print(f"ITAD search response for '{attempt}': {data}")
            
            # Handle the correct ITAD API response format
            game_id = None
            
            # Check if response is a direct list (newer API format)
            if isinstance(data, list) and data:
                game_id = data[0].get("id")
                if not game_id:  # Try 'plain' field as fallback
                    game_id = data[0].get("plain")
            # Check if response has data field (older API format)
            elif isinstance(data, dict) and "data" in data:
                if isinstance(data["data"], list) and data["data"]:
                    # Try both 'id' and 'plain' fields
                    first_result = data["data"][0]
                    game_id = first_result.get("id") or first_result.get("plain")
            
            # If we found a valid game_id, return it
            if game_id:
                print(f"Found ITAD ID '{game_id}' for search term '{attempt}'")
                return game_id
            else:
                print(f"No game ID found in response for '{attempt}'")
                # Continue to next attempt instead of failing
                
        except requests.exceptions.Timeout as e:
            last_error = ITADServiceError(f"ITAD title lookup timed out for '{attempt}'.")
            print(f"Timeout on attempt {i+1}/{len(attempts)} for '{attempt}': {e}")
            if i == len(attempts) - 1:  # Last attempt
                raise last_error
            continue
        except requests.exceptions.RequestException as e:
            last_error = ITADServiceError(f"Network error during ITAD title lookup for '{attempt}': {e}")
            print(f"Network error on attempt {i+1}/{len(attempts)} for '{attempt}': {e}")
            if i == len(attempts) - 1:  # Last attempt
                raise last_error
            continue
        except ValueError as e:
            last_error = ITADServiceError(f"Failed to parse JSON response for ITAD title lookup for '{attempt}': {e}")
            print(f"JSON parse error on attempt {i+1}/{len(attempts)} for '{attempt}': {e}")
            if i == len(attempts) - 1:  # Last attempt
                raise last_error
            continue
        except Exception as e:
            last_error = ITADServiceError(f"An unexpected error occurred during ITAD title lookup for '{attempt}': {e}")
            print(f"Unexpected error on attempt {i+1}/{len(attempts)} for '{attempt}': {e}")
            if i == len(attempts) - 1:  # Last attempt
                raise last_error
            continue

    # If we get here, no ID was found after all attempts
    print(f"No ITAD ID found for any search attempt for '{game_title}'")
    return None

def get_game_price(game_id: str) -> Optional[List[Dict]]:  # Fixed return type
    api_key = os.getenv("ITAD_API_KEY")
    base_url = "https://api.isthereanydeal.com"
    if not api_key:
        raise ITADServiceError("ITAD_API_KEY not set in environment variables.")

    url = f"{base_url}/games/prices/v3"

    headers = {
        "Content-Type": "application/json"
    }
    
    body = [game_id]
    
    params = {
        "key": api_key,
        "country": "GB"
    }
    
    try:
        response = requests.post(url, params=params, headers=headers, json=body, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Debug logging
        print(f"ITAD price response for '{game_id}': {data}")
        
        # FIXED: Handle the correct ITAD API response format
        if isinstance(data, list) and data:
            # API returns a list of game objects
            for game_data in data:
                if isinstance(game_data, dict) and game_data.get("id") == game_id:
                    deals = game_data.get("deals", [])
                    if isinstance(deals, list):
                        print(f"Found {len(deals)} price entries for '{game_id}'")
                        return deals
                    else:
                        print(f"Deals field is not a list for '{game_id}': {type(deals)}")
                        return []
            print(f"Game ID '{game_id}' not found in response list")
            return []
        else:
            print(f"Response is not a list or is empty: {data}")
            return []
             
    except requests.exceptions.Timeout:
        raise ITADServiceError(f"ITAD price lookup timed out for game '{game_id}'.")
    except requests.exceptions.RequestException as e:
        raise ITADServiceError(f"Network error fetching price for game '{game_id}': {e}")
    except ValueError as e:
        raise ITADServiceError(f"Failed to parse JSON response for ITAD price for game '{game_id}': {e}")
    except Exception as e:
        raise ITADServiceError(f"An unexpected error occurred fetching price for game '{game_id}': {e}")
    
    

 
    # if isinstance(data, dict) and "data" in data:
    #     for item in data["data"]:
    #         if item.get("id") == game_id:
    #             return item

   # return None
   
   # ^-- Don't think I need to above anymore, keeping just in case
   
