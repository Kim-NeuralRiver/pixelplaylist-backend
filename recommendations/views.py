from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .services.igdb_service import query_igdb_games
from .services.genre_service import fetch_igdb_genres
from .services.price_service import get_game_price, get_game_id
from .services.openai_service import generate_game_blurb
from .models import GamePlaylist
from .serializers import GamePlaylistSerializer
import logging


#Protect API views with JWT authentication
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

#API view to handle Post requests
# Needs JSON payload with 'genres' (IDs), platform (ID), and 'budget' (enriched using ITAD price data)
class GameRecommendationView(APIView): # Configure Swagger for input first
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
                price_info = get_game_price(plain_id) if plain_id else None

                game["price"] = {
                    "price": None,
                    "store": None,
                    "discount": None,
                    "url": None,
                }

                if price_info and "deals" in price_info and price_info["deals"]:
                    best_offer = price_info["deals"][0]
                    price_new = best_offer.get("price_new")
                    discount_pct = best_offer.get("price_cut")
                    currency = "GBP"

                    if isinstance(price_new, (int, float)) and price_new > budget:
                        continue

                    game["price"] = {
                        "price": price_new,
                        "store": best_offer.get("shop", {}).get("name"),
                        "discount": (
                            f"This game's price is ${price_new:.2f} after {discount_pct}% discount"
                            if discount_pct else None
                        ),
                        "currency": currency,
                        "url": best_offer.get("url"),
                    }

# Add OpenAI generated blurb regardless of price availability 

            try: 
                game["blurb"] = generate_game_blurb(game)
            except Exception as blurb_error: # Catch errors from OpenAI
                logger = logging.getLogger(__name__)
                logger.warning(f"Blurb generation failed for {game.get('title')}: {str(blurb_error)}")
                game["blurb"] = "Blurb generation failed. Please try again later."
                
                enriched_games.append(game)
            
            return Response(enriched_games, status=status.HTTP_200_OK)
        
        # Catch errors
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error("An error occurred while processing the request", exc_info=True)
            
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
# Return a list of genre IDs and names from IGDB API
class GenreListView(APIView):#
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
    serializer_class = GamePlaylistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GamePlaylist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)