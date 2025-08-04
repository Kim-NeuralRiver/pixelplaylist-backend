# Defines how data from the GamePlaylist model is serialized into JSON for the frontend, double checking this today
import logging
import json
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import GamePlaylist
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Configure structured logging for Cloud Run
logger = logging.getLogger(__name__)

# Set up structured logging format for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Cloud Run handles the formatting
)


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
            logger.warning(
                "User creation attempted with duplicate email",
                extra={
                    "severity": "WARNING",
                    "email": value,
                    "action": "user_create_validation"
                }
            )
            raise serializers.ValidationError("A user with this email already exists.")
        return value
        
    def validate_username(self, value): # Ensure username is unique and valid
        if User.objects.filter(username=value).exists():
            logger.warning(
                "User creation attempted with duplicate username",
                extra={
                    "severity": "WARNING",
                    "username": value,
                    "action": "user_create_validation"
                }
            )
            raise serializers.ValidationError("A user with this username already exists.")
        return value
        
    def create(self, validated_data):
        # Remove name from validated_data if present 
        name = validated_data.pop('name', '')
        
        # Log the user creation attempt with structured data
        logger.info(
            "Creating new user",
            extra={
                "severity": "INFO",
                "action": "user_create_start",
                "username": validated_data.get('username'),
                "email": validated_data.get('email'),
                "has_name": bool(name)
            }
        )
        
        try:
            user = User.objects.create_user(
                username=validated_data.get('username', None),
                email=validated_data.get('email', None),
                password=validated_data['password']
            )
            
            logger.info(
                "User created successfully",
                extra={
                    "severity": "INFO",
                    "action": "user_create_success",
                    "user_id": user.id,
                    "username": user.username
                }
            )
            
            # Store name in first_name and last_name if provided
            if name:
                name_parts = name.split(' ', 1)
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = name_parts[1]
                user.save()
                
                logger.info(
                    "User name fields updated",
                    extra={
                        "severity": "INFO",
                        "action": "user_name_update",
                        "user_id": user.id,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    }
                )
                
        except Exception as e:
            logger.error(
                "Failed to create user",
                extra={
                    "severity": "ERROR",
                    "action": "user_create_failed",
                    "error": str(e),
                    "username": validated_data.get('username')
                },
                exc_info=True
            )
            raise

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
            logger.warning(
                "Password change attempted with mismatched passwords",
                extra={
                    "severity": "WARNING",
                    "action": "password_change_validation"
                }
            )
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
    username = serializers.CharField(required=False, allow_blank=True)

    # Make username not required after init
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['username'].allow_blank = True
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
        
        # Log authentication attempt
        logger.info(
            "Authentication attempt",
            extra={
                "severity": "INFO",
                "action": "auth_attempt",
                "has_username": bool(username),
                "has_email": bool(email),
                "method": "email_token_obtain"
            }
        )
        
        # Check if have either username or email
        if not username and not email:
            logger.warning(
                "Authentication failed - no credentials provided",
                extra={
                    "severity": "WARNING",
                    "action": "auth_failed",
                    "reason": "no_credentials"
                }
            )
            raise serializers.ValidationError({
                "username": "Either username or email is required.",
                "email": "Either username or email is required."
            })
        
        if not password:
            logger.warning(
                "Authentication failed - no password provided",
                extra={
                    "severity": "WARNING",
                    "action": "auth_failed",
                    "reason": "no_password"
                }
            )
            raise serializers.ValidationError({
                "password": "This field is required."
            })

        # Different input scenarios: 
        if email and not username:        
            try:
                user = User.objects.only('username').get(email=email)
                attrs["username"] = user.username
                logger.info(
                    "User found by email",
                    extra={
                        "severity": "INFO",
                        "action": "user_lookup_success",
                        "method": "email",
                        "user_id": user.id
                    }
                )
            except User.DoesNotExist:
                logger.warning(
                    "Authentication failed - email not found",
                    extra={
                        "severity": "WARNING",
                        "action": "auth_failed",
                        "reason": "email_not_found",
                        "email": email
                    }
                )
                raise serializers.ValidationError({
                    "email": "No user found with this email address."
                })
                
        elif username and not email:
            try:
                user = User.objects.get(username=username)
                attrs["username"] = username
                logger.info(
                    "User found by username",
                    extra={
                        "severity": "INFO",
                        "action": "user_lookup_success",
                        "method": "username",
                        "user_id": user.id
                    }
                )
            except User.DoesNotExist:
                logger.warning(
                    "Authentication failed - username not found",
                    extra={
                        "severity": "WARNING",
                        "action": "auth_failed",
                        "reason": "username_not_found",
                        "username": username
                    }
                )
                raise serializers.ValidationError({
                    "username": "No user found with this username."
                })
                
        elif username and email:
            try:
                user = User.objects.get(username=username, email=email)
                attrs["username"] = username
                logger.info(
                    "User found by username and email",
                    extra={
                        "severity": "INFO",
                        "action": "user_lookup_success",
                        "method": "username_email",
                        "user_id": user.id
                    }
                )
            except User.DoesNotExist:
                logger.warning(
                    "Authentication failed - username/email combination not found",
                    extra={
                        "severity": "WARNING",
                        "action": "auth_failed",
                        "reason": "combo_not_found",
                        "username": username,
                        "email": email
                    }
                )
                raise serializers.ValidationError({
                    "username": "No user found with this username and email combination.",
                    "email": "No user found with this username and email combination."
                })
 
        attrs['password'] = password
        
        # Call parent validation but handle the case where username might be empty
        # We've already set username in attrs if email was provided
        return super().validate(attrs)
    
    def get_token(self, user):
        # Returns a JWT token for the given user, adding custom claims for email and username.
        token = super().get_token(user)
        token['email'] = user.email
        token['username'] = user.username
        
        logger.info(
            "JWT token generated",
            extra={
                "severity": "INFO",
                "action": "token_generated",
                "user_id": user.id,
                "username": user.username
            }
        )
        
        return token