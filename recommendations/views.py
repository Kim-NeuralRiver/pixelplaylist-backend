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
from rest_framework.exceptions import ValidationError
from .services.igdb_service import query_igdb_games
from .services.genre_service import fetch_igdb_genres
from .services.price_service import get_game_price, get_game_id
from .services.openai_service import generate_game_blurb
from .models import GamePlaylist
from .serializers import GamePlaylistSerializer, UserCreateSerializer
import logging

class UserCreateView(generics.CreateAPIView): # Registration view
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    
#API view to handle Post requests
# Needs JSON payload with 'genres' (IDs), platform (ID), and 'budget' (enriched using ITAD price data)
class GameRecommendationView(APIView): # Configure Swagger for input first
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'genres': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'platform': openapi.Schema(type=openapi.TYPE_INTEGER),
                'budget': openapi.Schema(type=openapi.TYPE_NUMBER),
            },
            required=['genres', 'platform', 'budget'],
            example={
                'genres': [21, 35, 2],  # Example genre IDs
                'platform': 6,       # Example platform ID
                'budget': 59.99      # Example budget
            }
        ),
        responses={200: 'List of game recommendations'}
    )

    def post(self, request): #extract data from payload
        genre_ids = request.data.get('genres')
        platform_id = request.data.get('platform')
        budget = request.data.get('budget') #price filtering
        
        # Input validation
        if not genre_ids or not platform_id or budget is None:
            return Response(
                {"error": "Invalid input. Please provide 'genres', 'platform', and 'budget'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # First, query IGDB for matching games
        try:
            games = query_igdb_games(genre_ids, platform_id)  
            
            enriched_games = []
            
            for game in games:
                title = game.get("title")
                plain_id = get_game_id(title)
                if not plain_id:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"No plain ID found for {title}.")
                    continue

                price_info = get_game_price(plain_id)
                if not price_info:
                    game["price_note"] = "Price data unavailable from ITAD."
                    logger.warning(f"No price information found for {title}.")
                    continue

                game["price"] = {
                    "price": None,
                    "store": None,
                    "discount": None,
                    "url": None,
                    "currency": "GBP"
                }

                if isinstance(price_info, list):
                    best_offer = None
                    lowest_price = float("inf")
                    
                    for deal in price_info:
                        price = deal.get("price_new")
                        if price is None:
                            continue # Skip if no price available 
                        
                        if price < lowest_price:
                            best_offer = deal
                            lowest_price = price
                        elif price == lowest_price:
                            if best_offer and best_offer.get("shop", {}).get("id") != "steam" and deal.get("shop", {}).get("id") == "steam":
                                best_offer = deal # Prefer Steam if prices are all the same
                                
                    if best_offer:
                        price_new = best_offer.get("price_new")
                        discount_pct = best_offer.get("price_cut")
                        currency = "GBP" # Can be adjusted if breaking
                        
                        # Skip games that go over budget
                        if isinstance(price_new, (int, float)) and price_new > budget:
                            game["price_note"] = f"Skipped: {title}, it exceeds the budget (£{price_new:.2f})"
                        else:
                            game["price"] = {
                                "price": price_new,
                                "store": best_offer.get("shop", {}).get("name"),
                                "discount": (
                                    f"This game's price is £{price_new:.2f} after {discount_pct}% discount"
                                    if discount_pct else None # if no discount, set to None
                                ),
                                "currency": currency,
                                "url": best_offer.get("url"),
                            }
                            
# Add OpenAI generated blurb regardless of price availability 

                try: 
                    game["blurb"] = generate_game_blurb(game)
                except Exception as blurb_error:  # Catch errors from OpenAI
                    logger.warning(f"Blurb generation failed for {game.get('title', 'Unknown Title')}: {str(blurb_error)}")
                    game["blurb"] = "Blurb generation failed. Please try again later."
                
                # Always append the game after processing blurb, even if an exception occurs
                enriched_games.append(game)
                logger.info(f"Processed game: {game.get('title')}")

            if not enriched_games:
                logger.info("No games found matching the criteria.")
                return Response()

            logger.info(f"Returning {len(enriched_games)} enriched games out of {len(games)} IGDB results")
            return Response(enriched_games, status=status.HTTP_200_OK)


        # Catch errors
        except Exception as e:
            logger.error("An error occurred while processing the request", exc_info=True)

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
# Return a list of genre IDs and names from IGDB API
class GenreListView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retrieve IGDB genres",
        responses={200: "List of genres"}
    )
    def get(self, request):
        try:
            genres = fetch_igdb_genres()
            return Response(genres, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class GamePlaylistListCreate(generics.ListCreateAPIView): # Save playlists to the database
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'games': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                ),
            },
            required=['name', 'games'],
            example={
                "name": "Fantasy RPGs",
                "games": [
                    {"title": "Bastion", "price": 24.99, "store": "Steam"},
                    {"title": "Celeste", "price": 19.99, "store": "GOG"}
                ]
            }
        )
    )
    def post(self, request, *args, **kwargs): # Handle playlist creation
        return super().post(request, *args, **kwargs) 
    
    serializer_class = GamePlaylistSerializer # Serializer for playlist data

    def get_queryset(self): # Retrieve playlists
        return GamePlaylist.objects.filter(user=self.request.user)

    def perform_create(self, serializer): # Create / Save playlist with user data
        name = self.request.data.get("name")
        games = self.request.data.get("games")
        
        if not name or not games: 
            raise serializers.ValidationError("Both 'name' and 'games' are necessary to create a playlist.")
        
        serializer.save(user=self.request.user, name=name, games=games) # Users only see their own data             raise ValidationError({"detail": "Both 'name' and 'games' are necessary to create a playlist."})
