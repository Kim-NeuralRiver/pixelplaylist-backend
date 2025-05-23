from django.urls import path
from .views import GameRecommendationView, GenreListView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('recommendations/', GameRecommendationView.as_view(), name='recommendations'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Add more paths if / when needed
]
