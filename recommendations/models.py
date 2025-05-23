from django.contrib.auth.models import User
from django.db import models

class GamePlaylist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    games = models.JSONField()  # Store list of game recommendation dicts
    created_at = models.DateTimeField(auto_now_add=True)
