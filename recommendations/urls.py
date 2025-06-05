# Connects all backend views to their respective API endpoints (/api/recommendations/, /api/playlists/, etc.
from django.urls import path
from .views import (
    GameRecommendationView,
    GenreListView,
    GamePlaylistListCreate,
    UserCreateView
)

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='game-recommendations'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('playlists/', GamePlaylistListCreate.as_view(), name='playlist-list-create'),
    path('users/', UserCreateView.as_view(), name='user-create'),
]
