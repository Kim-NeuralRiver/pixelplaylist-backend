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
    
# User create serializer
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name']
        read_only_fields = ['id', 'username']
 
 # Change pass serializer       
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True, min_length=8)
    new_password2 = serializers.CharField(required=True, min_length=8)
    
    def validate_new_password2(self,value):
        if value != self.initial_data.get('new_password1'):
            raise serializers.ValidationError("New passwords do not match.")
        return value
    
# serializer for validating input to GameRecommendationView
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
    email = serializers.EmailField(required=False, allow_blank=True) 
    username = serializers.CharField(required=False, allow_blank=True, allow_empty=True, allow_null=True)

    # Make username not required after init
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['email'].required = False
        # Remove username from required fields if it exists
          
    # add custom validation methods for sign in
    def validate_email(self, value):
        if value is not None:
            value = value.strip()
            if not value:  # Empty after stripping
                return None
        return value
    
    def validate_username(self, value):
        if value is not None:
            value = value.strip()
            if not value:  # Empty after stripping
                return None
        return value
    
    def validate(self, attrs):
        """
        Original comment block included for context / fallback:
        Get from initial_data and strip whitespace
        Use already validated and stripped values from attrs
        username = attrs.get("username", "")
        email = attrs.get("email", "")
        password = attrs.get("password", "").strip()
        # Check if we have either username or email
        if not username and not email:
            raise serializers.ValidationError({
                "username": "This field is required.",
                "email": "This field is required."
            })
        """
        
        """
        Changes made most recently (for debugging purposes):
        1. Better handling of empty strings vs None values
        2. Improved error messaging to clarify that either username OR email is needed
        3. Removed redundant stripping - relying on field-level validation
        4. Removed commented-out code that was no longer relevant
        5. Simplified the logic flow for cleaner validation
        """
        
        # Use already validated and stripped values from attrs
        username = attrs.get("username")  # Will be None if not provided, "" if empty string
        email = attrs.get("email")
        password = attrs.get("password", "")
        
        # Convert empty strings to None after individual field validation
        if username == "":
            username = None
        if email == "":
            email = None
        
        # Check if have either username or email
        if not username and not email:
            raise serializers.ValidationError({
                "username": "Either username or email is required.",
                "email": "Either username or email is required."
            })
        
        if not password:
            raise serializers.ValidationError({
                "password": "This field is required."
            })

        # Different input scenarios: 
        if email and not username:        
            try:
                user = User.objects.only('username').get(email=email)
                attrs["username"] = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    "email": "No user found with this email address."
                })
                
        elif username and not email:
            try:
                User.objects.get(username=username)
                attrs["username"] = username
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    "username": "No user found with this username."
                })
                
        elif username and email:
            try:
                user = User.objects.get(username=username, email=email)
                attrs["username"] = username
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    "username": "No user found with this username and email combination.",
                    "email": "No user found with this username and email combination."
                })
 
        attrs['password'] = password
        return super().validate(attrs)
    
    def get_token(self, user):
        # Returns a JWT token for the given user, adding custom claims for email and username.
        token = super().get_token(user)
        token['email'] = user.email
        token['username'] = user.username
        return token