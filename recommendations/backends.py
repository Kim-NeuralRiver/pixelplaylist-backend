# Custom auth backend to handle both username and email login options
# If this doesn't work, I don't know what will

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try email first
            user = User.objects.get(email=username) # Attempt to find user by email
            if user.check_password(password) and user.is_active: # If the account exists and is active, check password val
                return user
        except User.DoesNotExist:
            # Fall back to username
            try:
                user = User.objects.get(username=username) # Attempt to find user by username
                if user.check_password(password) and user.is_active: 
                    return user
            except User.DoesNotExist:
                pass
        return None 