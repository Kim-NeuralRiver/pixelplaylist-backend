# Defines how data from the GamePlaylist model is serialized into JSON for the frontend, double checking this today
from rest_framework import serializers
from .models import GamePlaylist

class GamePlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamePlaylist
        fields = ['id', 'name', 'games', 'created_at', 'user']
        read_only_fields = ['id']