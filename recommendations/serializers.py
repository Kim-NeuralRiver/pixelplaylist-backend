# Defines how data from the GamePlaylist model is serialized into JSON for the frontend, double checking this today
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import GamePlaylist
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class GamePlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamePlaylist
        fields = ['id', 'name', 'games', 'created_at', 'user']
        read_only_fields = ['id', 'created_at', 'user'] # 
        

# User create serializer using Django's built in user model 
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # 'name' is a virtual field used for user creation, not stored in the User model
    name = serializers.CharField(required=False, allow_blank=True, help_text="Full name (not stored in User model, split into first_name and last_name).")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'name']
        
    def validate_email(self, value): # Ensure email is unique and valid
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
        
    def validate_username(self, value): # Ensure username is unique and valid
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
        
    def create(self, validated_data):
        # Remove name from validated_data if present 
        name = validated_data.pop('name', '')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        # Store name in first_name and last_name if provided
        if name:
            name_parts = name.split(' ', 1)
            user.first_name = name_parts[0]
            if len(name_parts) > 1:
                user.last_name = name_parts[1]
            user.save()
            
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
    platform = serializers.ListField(  # accepts a list like genres
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
    
    
# Custom serializer for email/pass as well as user/pass login

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    
    def validate(self, attrs):
        email = self.initial_data.get("email")
        password = self.initial_data.get("password")
        
        if not email:
            raise serializers.ValidationError({"email": "This field is required."})
        if not password: 
            raise serializers.ValidationError({"password": "This field is required."})
            
        # Workaround: Set 'username' to the email for JWT authentication.
        # Note: This assumes that the username and email are always the same.
        # If usernames and emails diverge, this may cause authentication issues.
        attrs["username"] = email
        
        return super().validate(attrs)
    
    def get_token(self, user):
        token = super().get_token(user)
        token['email'] = user.email
        return token