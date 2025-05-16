from django.urls import path
from .views import GameRecommendationView

print("Loaded recommendations.urls") # Debug, remove later

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='game-recommendations'),
]
