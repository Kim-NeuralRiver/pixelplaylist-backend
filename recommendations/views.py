# Main logic for handling recommendation requests, genre fetching, and playlist saving, integrates external APIs and routes results back to the frontend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from .services.igdb_service import query_igdb_games, IGDBServiceError # Services imports
from .services.genre_service import fetch_igdb_genres, GenreServiceError
from .services.price_service import get_game_price, get_game_id, ITADServiceError
from .services.openai_service import generate_game_blurb, OpenAIServiceError
from .models import GamePlaylist
from .serializers import GamePlaylistSerializer, UserCreateSerializer, GameRecommendationInputSerializer, EmailTokenObtainPairSerializer # Serializer imports
import logging
import requests 
from concurrent.futures import ThreadPoolExecutor, as_completed # For concurrent processing

# Logger instantiation for the module
logger = logging.getLogger(__name__)

# User Registration View
class UserCreateView(generics.CreateAPIView): 
    queryset = User.objects.all() # User creation queryset to allow registration 
    serializer_class = UserCreateSerializer 
    permission_classes = [permissions.AllowAny] # Ensure users aren't blocked from signing up
    
    @swagger_auto_schema(
        request_body=UserCreateSerializer,
        responses={
            201: openapi.Response(
                description="User created successfully", 
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={ # Define the response schema for successful user creation
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING),
                        'username': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                        'email': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                        'password': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs): # post method for user creation
        try:
            return super().create(request, *args, **kwargs)
        except serializers.ValidationError:
            raise # Raise 400 bad req if validation fails
        except Exception as e:
            logger.error(f"User creation failed: {e}", exc_info=True)
            return Response(
                {"detail": "User creation failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
# API view to handle Post requests for game recommendations
# Needs JSON payload with 'genres' (IDs), platform (ID), and 'budget' (enriched using ITAD price data)
class GameRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    # Configure Swagger for input using the new serializer
    @swagger_auto_schema(
        request_body=GameRecommendationInputSerializer, # Use the serializer for request body definition
        responses={
            200: openapi.Response(
                description="List of game recommendations, potentially with price and blurb.",
                # Improved the response schema to include necessary fields and handle errors better
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Game title"),
                            'cover_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="URL to game cover image"),
                            'platform': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of platform names"),
                            'summary': openapi.Schema(type=openapi.TYPE_STRING, description="Game summary"),
                            'genres': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of genre names"),
                            'price': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                description="Price information from ITAD",
                                properties={
                                    'price': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                                    'store': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'discount': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'currency': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            ),
                            'price_note': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Note regarding price availability or budget exceedance"),
                            'blurb': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="OpenAI generated recommendation blurb"),
                        }
                    )
                )
            ),
            400: "Invalid input provided",
            401: "Authentication credentials were not provided",
            424: "External API dependency failed (e.g., IGDB, ITAD, OpenAI issues)",
            503: "Service Unavailable (network error during external API calls)",
            500: "Internal server error"
        }
    )
    def post(self, request):
        # Validate incoming request data with the GameRecommendationInputSerializer
        serializer = GameRecommendationInputSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True) # Automatically raise a ValidationError (400) if input is invalid
            validated_data = serializer.validated_data
            
            genre_ids = validated_data['genres'] 
            platform_id = validated_data['platform']
            budget = validated_data['budget']
            
        except serializers.ValidationError as e:
            logger.warning(f"Invalid input for game recommendation: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        initial_games = [] # Store games from IGDB before enrichment
        enriched_games = [] # Final list of processed games

        try:
            # First, query IGDB for matching games
            # Handle potential service errors from IGDB query
            initial_games = query_igdb_games(genre_ids, platform_id, limit=5) # Custom limit parameter for max number of games to call
            
            if not initial_games:
                logger.info("No games found from IGDB matching the specified criteria.")
                # Return an empty list with a message for no matches if no games found
                return Response(
                    {"message": "No games found matching your criteria. Try different genres or platforms."}, 
                    status=status.HTTP_200_OK
                )

            # Added ThreadPoolExecutor to run enrichment for each game in parallel to help with performance issues
            # Max workers can be adjusted based on API rate limits and server resources
            with ThreadPoolExecutor(max_workers=5) as executor: # Limit concurrent API calls
                # Submit enrichment task for each game
                future_to_game = { 
                    executor.submit(self._enrich_game_data, game.copy(), budget): game # Use copy to avoid modifying original game data
                    for game in initial_games 
                }

                # Collect results as they complete
                for future in as_completed(future_to_game):
                    original_game_title = future_to_game[future].get('title', 'Unknown Title') 
                    try:
                        enriched_game = future.result() 
                        if enriched_game:
                            enriched_games.append(enriched_game)
                    except (ITADServiceError, OpenAIServiceError, requests.exceptions.RequestException) as exc:
                        # Catch specific errors from enrichment process
                        logger.warning(f"Partial enrichment failed for '{original_game_title}': {exc}. Adding with note.")
                        # If enrichment fails for a game, return it with an error note
                        
                        original_game = future_to_game[future] # Get the original game dictionary
                        original_game["status_note"] = f"Enrichment failed: {exc}" # Add a status note
                        enriched_games.append(original_game) # Append the original game with error note
                        
                    except Exception as exc:
                        logger.error(f"An unexpected error occurred during enrichment for '{original_game_title}': {exc}", exc_info=True)
                        original_game = future_to_game[future]
                        original_game["status_note"] = "An unexpected error occurred during enrichment."
                        enriched_games.append(original_game)

            if not enriched_games:
                logger.info("No games could be fully enriched after initial IGDB query.")
                # If all games failed enrichment or were filtered out 
                return Response(
                    {"message": "No games could be enriched with price/blurb data. Please try again later."},
                    status=status.HTTP_200_OK # Still 200 OK as the initial query succeeded
                )

            logger.info(f"Returning {len(enriched_games)} enriched games out of {len(initial_games)} IGDB results.")
            return Response(enriched_games, status=status.HTTP_200_OK)

        # Exception Handling for external API calls
        except IGDBServiceError as e:
            # Catch errors from the IGDB service
            logger.error(f"IGDB service error: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to retrieve games from IGDB: {e}"},
                status=status.HTTP_424_FAILED_DEPENDENCY # Indicates dependency failure
            )
        except requests.exceptions.RequestException as e:
            # Catch network-related errors for  external API calls
            logger.error(f"Network error during game recommendation process: {e}", exc_info=True)
            return Response(
                {"error": "A network error occurred while connecting to external game services. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE # Indicates service is temporarily unavailable
            )
        except Exception as e:
            # Catch any other unexpected errors not specifically handled
            logger.error("An unexpected internal error occurred while processing the game recommendation request", exc_info=True)
            return Response(
                {"error": "An internal server error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Enrich game dict with price and blurb info, used by ThreadPoolExecutor
    def _enrich_game_data(self, game: dict, budget: float) -> dict:
        
        title = game.get("title") 
        if not title:
            logger.warning("Skipping enrichment for a game with no title.")
            return None
            
        # Initialize response structure
        game["price"] = {
            "price": None,
            "store": None,
            "discount": None,
            "url": None,
            "currency": "GBP"
        }
        game["price_note"] = None
        game["blurb"] = None
        
        # ITAD Plain ID lookup
        plain_id = None 
        try:
            plain_id = get_game_id(title)
            if not plain_id:
                game["price_note"] = "Price data unavailable: No ITAD plain ID found."
                logger.warning(f"No plain ID found for '{title}'.")
            else:
                logger.debug(f"Found ITAD ID '{plain_id}' for game '{title}'")
        except ITADServiceError as e:
            game["price_note"] = f"Price data unavailable: ITAD plain ID lookup failed ({str(e)})."
            logger.warning(f"ITAD plain ID lookup failed for '{title}': {e}")
        except Exception as e:
            game["price_note"] = f"Price data unavailable: Unexpected error during ITAD plain ID lookup."
            logger.error(f"Unexpected error during ITAD plain ID lookup for '{title}': {e}", exc_info=True)
        
        # Only proceed with price lookup if plain_id was successfully retrieved
        if plain_id:
            try:
                price_info = get_game_price(plain_id)
                if price_info and isinstance(price_info, list) and len(price_info) > 0:
                    self._process_price_info(game, price_info, budget, title)
                else:
                    current_note = game.get("price_note", "")
                    additional_note = " No deals found on ITAD."
                    game["price_note"] = (current_note + additional_note).strip() if current_note else additional_note.strip()
                    logger.warning(f"No price information (deals) found for '{title}'.")
                    
            except ITADServiceError as e:
                current_note = game.get("price_note", "")
                additional_note = f" ITAD price lookup failed ({str(e)})."
                game["price_note"] = (current_note + additional_note).strip() if current_note else additional_note.strip()
                logger.warning(f"ITAD price lookup failed for '{title}' (ID: {plain_id}): {e}")
            except Exception as e:
                current_note = game.get("price_note", "")
                additional_note = f" Unexpected error during price lookup."
                game["price_note"] = (current_note + additional_note).strip() if current_note else additional_note.strip()
                logger.error(f"Unexpected error during ITAD price lookup for '{title}' (ID: {plain_id}): {e}", exc_info=True)

        # Add OpenAI generated blurb (only once)
        try: 
            game["blurb"] = generate_game_blurb(game)
        except OpenAIServiceError as blurb_error:
            logger.warning(f"Blurb generation failed for '{title}': {str(blurb_error)}")
            game["blurb"] = f"Blurb generation failed. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error during blurb generation for '{title}': {e}", exc_info=True)
            game["blurb"] = "An unexpected error occurred during blurb generation."
        
        return game

    def _process_price_info(self, game: dict, price_info: list, budget: float, title: str):
  
        best_offer = None
        lowest_price = float("inf")
        
        for deal in price_info:
            
            price = deal.get("price", {}).get("amount")  # Changed from "price_new"
            if price is None or not isinstance(price, (int, float)):
                continue
            
            # Prioritize Steam if prices are equal, otherwise choose lowest
            if price < lowest_price:
                best_offer = deal
                lowest_price = price
            elif price == lowest_price and best_offer:
                # Prefer Steam if prices are identical
                current_shop = best_offer.get("shop", {}).get("name", "")  # Changed from "id" to match ITAD field names
                new_shop = deal.get("shop", {}).get("name", "")
                if current_shop.lower() != "steam" and new_shop.lower() == "steam":
                    best_offer = deal
                        
        if best_offer:
            price_amount = best_offer.get("price", {}).get("amount")
            discount_pct = best_offer.get("cut", 0)  # Changed from "price_cut", again to match field name
            
            # Check if the best offer exceeds the user's budget
            if isinstance(price_amount, (int, float)) and price_amount > budget:
                game["price_note"] = f"Game exceeds budget: £{price_amount:.2f} (budget: £{budget:.2f})."
            else:
                shop_info = best_offer.get("shop", {})
                game["price"] = {
                    "price": price_amount,
                    "store": shop_info.get("name", "Unknown Store"),
                    "discount": (
                        f"£{price_amount:.2f} after {discount_pct}% discount"
                        if discount_pct and discount_pct > 0 else None
                    ),
                    "currency": "GBP",
                    "url": best_offer.get("url"),
                }
                game["price_note"] = None  # Note if price was successfully added
        else:
            current_note = game.get("price_note", "")
            additional_note = " No suitable offers found."
            game["price_note"] = (current_note + additional_note).strip()
            
class GenreListView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Retrieve IGDB genres",
        responses={
            200: "List of genres",
            401: "Authentication credentials were not provided",
            424: "External API dependency failed (IGDB token error)",
            503: "Service Unavailable (network error)",
            500: "Internal server error"
        }
    )
    def get(self, request):
        try:
            genres = fetch_igdb_genres()
            return Response(genres, status=status.HTTP_200_OK)
        except GenreServiceError as e:
            logger.error(f"Genre service error: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to retrieve genres: {e}"},
                status=status.HTTP_424_FAILED_DEPENDENCY
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching IGDB genres: {e}", exc_info=True)
            return Response(
                {"error": "A network error occurred while fetching genres. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching IGDB genres: {e}", exc_info=True)
            return Response(
                {"error": "An internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class GamePlaylistListCreate(generics.ListCreateAPIView): # Save playlists to the database
    # Add permission classes here for security!
    permission_classes = [IsAuthenticated]
    serializer_class = GamePlaylistSerializer # Serializer for playlist data

    @swagger_auto_schema(
        request_body=GamePlaylistSerializer, # Use the serializer for request body
        responses={
            201: "Playlist created successfully",
            200: "List of user's playlists",
            400: "Invalid input",
            401: "Unauthorized"
        }
    )
   # def post(self, request, *args, **kwargs): # Handle playlist creation
   #     return super().post(request, *args, **kwargs) 

    def get_queryset(self): # Retrieve playlists
        return GamePlaylist.objects.filter(user=self.request.user)

    def perform_create(self, serializer): # Create / Save playlist with user data
        serializer.save(user=self.request.user) # Users only see their own data        
        
# Custom email token obtain view for registration

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer 
    
    @swagger_auto_schema(
        request_body=EmailTokenObtainPairSerializer, 
        operation_description="Obtain JWT token pair using email and password",
        responses={
            200: openapi.Response("JWT Token Pair"),
            400: openapi.Response(
                description="Invalid credentials",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'non_field_errors': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of validation errors")
                    }
                )
            ),
            }
        
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
