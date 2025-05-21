import os
import openai
from typing import Dict

# Generate a short, catchy, recommendation blurb for a game using OpenAI's GPT model.
# Args: game (dict): A dictionary containing game metadata such as title, genres, platforms, and summary.
# Returns: str: a short 1 - 2 sentence AI generated blurb

def generate_game_blurb(game: Dict) -> str: # lazy load API key on demand
    openai.api_key2 = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in environment variables.")
    
    openai.api_key = openai.api_key
    
    # Construct prompt for GPT
    title = game.get("title", "Unknown Title")
    genres = ",".join(game.get("genres", [])) or "Various Genres"
    platform = ",".join(game.get("platforms", [])) or "Various Platforms"
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
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75,
            max_tokens=100,
        )
        return response.choices[0].message['content'].strip()
    
    except openai.error.OpenAIError as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    except Exception as e:
        raise RuntimeError(f"Unexpected error occured during blurb generation: {str(e)}")
