from openai import OpenAI, OpenAIError
import os
from typing import Dict
import requests

# Define custom exception for OpenAI service failures
class OpenAIServiceError(RuntimeError):
    """Custom exception for errors specifically from the OpenAI service."""
    pass

def generate_game_blurb(game: Dict, user_query: Dict = None) -> str:
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
    user_context = ""
    if user_query:
        requested_genres = user_query.get("genres", [])
        requested_platform = user_query.get("platform")
        budget = user_query.get("budget")
        
        if requested_genres:
            user_context += f"The user specifically searched for {', '.join(requested_genres)} games. "
        if requested_platform:
            user_context += f"They are looking for games available on {requested_platform}. "
        if budget: 
            user_context += f"Their budget is {budget}. "
    
    # Provide examples but reduce quantity to focus on variety
    opening_line_examples = (        
        f"- It's weird. It's wonderful. It will run like smooth, smooth butter on your {platform}.\n" 
        f"- You haven't lived if you haven't explored ancient ruins while listening to an epic orchestral soundtrack.\n" 
        f"- If George Lucas, Steven King, and Hideo Kojima got together to make a game, it might look like this.\n" 
    )

    # Add negative examples of what to avoid
    repetitive_patterns_to_avoid = (
        f"- 'Stop! If you're looking for...'\n"
        f"- 'It's like if [famous person] made a [genre] game...'\n"
        f"- 'Budget-friendly doesn't mean boring...'\n"
        f"- Starting multiple blurbs with 'If you like...'\n"
        f"- Using the same adjectives like 'epic', 'amazing', or 'incredible' across blurbs\n"
    )

    prompt = (
        f"You are an expert game curator and playlist writer for a video game discovery app.\n"
        f"Write a short, highly engaging, and personalised recommendation blurb "
        f"for the following game, aimed at players who enjoy a specific genre and are seeking new experiences:\n\n"
        f"Title: {title}\n"
        f"Genres: {genres}\n"
        f"Platforms: {platform}\n"
        f"Summary: {summary}\n"
        f"{f'User Context: {user_context}' if user_context else ''}\n\n"
        f"Your response should:\n"
        f"- Reference {user_context} if provided, otherwise focus on the game itself.\n"
        f"- Be concise but use descriptive sentences.\n"
        f"- Keep to minimum length of 50 words and a maximum length of 85 words.\n"
        f"- Never cut off the blurb mid-sentence; ensure it is a complete thought.\n"
        f"- Create a COMPLETELY UNIQUE opening line specific to THIS game's mechanics, theme or style.\n"
        f"- Analyze the game's unique features and center your blurb around what makes THIS game stand out.\n"
        f"- You may draw inspiration from these creative opening styles: {opening_line_examples}\n"
        f"- AVOID THESE REPETITIVE PATTERNS: {repetitive_patterns_to_avoid}\n"
        f"- Vary tone between blurbs: sometimes be cinematic, sometimes conversational, sometimes quirky.\n"
        f"- Use sentence structures unique to this blurb - vary between short punchy sentences and flowing descriptive ones.\n" 
        f"- If user context is provided, tailor the blurb to their specific search criteria and budget.\n"
        f"- Reference the genre(s) indirectly through themes, tone, or mechanics instead of naming them directly.\n"
        f"- Highlight a SPECIFIC aspect of the game (ONE unique mechanic, art style detail, or narrative element).\n"
        f"- Be upbeat, intelligent, and reader-friendly.\n"
        f"- Avoid clichés like 'a must-play' or 'you won't regret it'.\n"
        f"- Avoid spoilers.\n"
        f"- Respond only with the recommendation blurb. Do not include quotes, labels, or any placeholder text.\n"
        f"- Each blurb MUST feel custom-written specifically for this game - readers should never feel they're seeing a template.\n"
    )
    

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.85,  # Slightly increased for more creativity
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
