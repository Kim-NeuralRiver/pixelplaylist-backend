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
    
    opening_line_examples = (        
        f"1) It's weird. It's wonderful. It will run like smooth, smooth butter on your {platform}.\n" 
        f"2) You haven't lived if you haven't [GAME ACTIVITY] while listening to an epic soundtrack like [GAME SOUNDTRACK].\n" 
        f"3) If George Lucas, Steven King, and [GAME DEVELOPER EXAMPLE] got together to make a game, it might look a little like this.\n" 
        f"4) Stop! If you're looking for some hammer time, look no further than {title}.\n" 
        f"5) Simply {title}. This low-budget work-of-art is a labour of love that proves creativity and a dream > cash and giant studios every day of the week. Be prepared to laugh, cry, and be filled with wonder as you sink hours into {title}.\n" 
        f"6) Do you want to [GAME ACTIVITY] with [ICONIC GAME MECHANIC OR WEAPON], well now you can!\n" 
        f"7) It's like if [ICONIC DIRECTOR] made a {genres} game, simply just because [DIRECTOR'S PRONOUN] could.\n" 
        f"8) Budget-friendly doesn't mean boring - this hidden gem punches way above its price tag - especially with the sweet deals we've rooted out for you!\n" 
        f"9) If you like {genres} and you're looking for a sweet new addition to your {platform}, look no further!\n" 
    )

# TO-DO (if all else fails): add previous opening sentence tracking / penalise repetition
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
        f"- Write a unique, original, and engaging opening line. Avoid reusing phrases across different blurbs.\n"
        f"- You may draw inspiration from off-beat, humorous, or cinematic-style openings like these examples: {opening_line_examples}. These are just illustrative – do not copy or reuse them verbatim. Always craft a fresh, original opening tailored to the specific game.\n"
        f"- Vary tone, sentence structure, and focal points between blurbs.\n"
        f"- Occasionally adopt the tone of a film trailer, tour guide, recipe, personal diary, surreal travel guide, or enthusiastic friend; choose whatever best suits the game. Just make sure it feels authentic.\n" 
        f"- If user context is provided, tailer the blurb to their specific search criteria and budget, specify why the game is good fit for the genres mentioned and the user's specific interests.\n"
        f"- Use an off-beat opening line, ensuring it is engaging specific to the game.\n"
        f"- Reference the genre(s) in a natural and varied way; feel free to hint at them through themes, tone, or mechanics instead of always naming them directly.\n"
        f"- Highlight why the game is appealing (gameplay, story, tone, uniqueness, art style).\n"
        f"- Explain what makes the game great on the user's platform of choice.\n"
        f"- Be upbeat, intelligent, and reader-friendly.\n"
        f"- Avoid clichés like 'a must-play' or 'you won’t regret it'\n"
        f"- Avoid spoilers\n"
        f"- Respond only with the recommendation blurb. Do not include quotes, labels, or any placeholder text (such as [GAME DEVELOPER], [GAME ACTIVITY], *Title*, or similar)."
        f"- Fill in any placeholder text (for example, [GAME DEVELOPER], [GAME ACTIVITY], [GAME SOUNDTRACK], [ICONIC GAME MECHANIC OR WEAPON]) with relevant information, (e.g. 'Rockstar Games', 'shoot zombies with a shotgun', 'thrilling heavy metal soundtrack', 'katana').\n"
        f"- Each blurb should start with a *distinct*, game-specific hook. Avoid reusing phrases across blurbs, especially in the opening sentence.\n"
        f"- Do not reuse wording from previous blurbs. Vary tone, phrasing, sentence structure, and focal points (e.g. theme, mechanics, tone, art style).\n"
        f"- Avoid starting with phrases like 'Stop! If you're looking for...' or '[Title] is a...' unless it is highly customised and fits the game (e.g. 'Warhammer' might fit the 'hammer time' opening).\n"
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
