# Defines how data from the GamePlaylist model is serialized into JSON for the frontend, double checking this today
from rest_framework import serializers
from .models import GamePlaylist
from django.contrib.auth.models import User

class GamePlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamePlaylist
        fields = ['id', 'name', 'games', 'created_at', 'user']
        read_only_fields = ['id', 'created_at', 'user']
        

# User create serializer using Django's built in user model 
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    
# New serializer for validating input to GameRecommendationView
# Ensures that genres is a list of ints, platform is an int, and budget is non-negative (number)
class GameRecommendationInputSerializer(serializers.Serializer):
    genres = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        default=[21, 35, 2],
        help_text="A list of genre IDs, e.g.: [21, 35, 2]."
    )
    platform = serializers.ListField(  # CHANGED: Now accepts a list like genres
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        default=[6],  # Changed to list format, will see if this works better
        help_text="A list of platform IDs, e.g.: [6, 49] for PC and Xbox."
    )
    budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100,
        min_value=0,
    )