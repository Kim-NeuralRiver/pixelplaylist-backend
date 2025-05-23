from django.urls import path
from .views import GameRecommendationView, GenreListView

print("Loaded recommendations.urls") # Debug, remove later

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='recommendations'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    # Add more paths if / when needed
]
