# Defines the GamePlaylist database model, each playlist is tied to a user and includes a name and a JSON blob of games
from django.contrib.auth.models import User
from django.db import models

class GamePlaylist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    games = models.JSONField()  # Store list of game recommendation dicts
    created_at = models.DateTimeField(auto_now_add=True)
