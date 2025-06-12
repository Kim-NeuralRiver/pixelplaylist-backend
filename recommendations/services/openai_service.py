from openai import OpenAI, OpenAIError
import os
from typing import Dict
import requests

# Define custom exception for OpenAI service failures
class OpenAIServiceError(RuntimeError):
    """Custom exception for errors specifically from the OpenAI service."""
    pass

def generate_game_blurb(game: Dict) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIServiceError("OPENAI_API_KEY not set in environment variables.")

    client = OpenAI(api_key=api_key)

    # Use .get() with default values to handle potentially missing keys from game data
    title = game.get("title", "Unknown Title")
    # If genres or platforms are missing, provide a default value
    genres = ",".join(game.get("genres", [])) or "Various Genres"
    platform = ",".join(game.get("platform", [])) or "Various Platforms"
    summary = game.get("summary", "No summary available.")

    prompt = (
        f"You are an expert game curator for a video game discovery app.\n"
        f"Write a short, highly engaging and personalized recommendation blurb "
        f"for the following game, aimed at players seeking new experiences:\n\n"
        f"Title: {title}\n"
        f"Genres: {genres}\n"
        f"Platforms: {platform}\n"
        f"Summary: {summary}\n\n"
        f"Your response should:\n"
        f"- Be 1–2 concise but descriptive sentences\n"
        f"- Highlight why the game is appealing (gameplay, story, tone, uniqueness)\n"
        f"- Be upbeat, intelligent, and reader-friendly\n"
        f"- Avoid clichés like 'a must-play' or 'you won’t regret it'\n"
        f"- Avoid spoilers\n\n"
        f"Respond only with the recommendation blurb. Do not include quotes or labels like 'Recommendation:'."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75,
            max_tokens=100,
            timeout=10  # Set a timeout to prevent hanging requests
        )
        return response.choices[0].message.content.strip()

    except OpenAIError as e: # Catch specific OpenAI API errors
        raise OpenAIServiceError(f"OpenAI API error during blurb generation: {str(e)}")
    except requests.exceptions.Timeout:
        raise OpenAIServiceError("OpenAI blurb generation request timed out.")
    except requests.exceptions.RequestException as e:
        # Catch underlying network errors that requests might raise (OpenAI client uses requests)
        raise OpenAIServiceError(f"Network error during OpenAI blurb generation: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors during blurb generation
        raise OpenAIServiceError(f"An unexpected error occurred during blurb generation: {str(e)}")
