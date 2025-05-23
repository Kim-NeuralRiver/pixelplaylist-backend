from django.urls import path
from .views import (
    GameRecommendationView,
    GenreListView,
    GamePlaylistListCreate,
)

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='game-recommendations'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('playlists/', GamePlaylistListCreate.as_view(), name='playlist-list-create'),
]
