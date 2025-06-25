# Connects all backend views to their respective API endpoints (/api/recommendations/, /api/playlists/, etc.
from django.urls import path
from .views import (
    GameRecommendationView,
    GenreListView,
    GamePlaylistListCreate,
    UserCreateView,
    UserProfileView,
    ChangePasswordView
)

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='game-recommendations'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('playlists/', GamePlaylistListCreate.as_view(), name='playlist-list-create'),
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/change-password/', ChangePasswordView.as_view(), name='change-password'),
]
