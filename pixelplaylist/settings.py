import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import dj_database_url

# Environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Detect environment (dev or prod)
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")
DEBUG = ENVIRONMENT == "development" 

# Secret key
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "fallback-insecure-dev-key")

# Allowed hosts
if DEBUG:
    ALLOWED_HOSTS = ["*"] # Allow all hosts in development
else:
    ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "pixelplaylist.onrender.com").split(",") # Allow multiple hosts

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_yasg',
    'rest_framework',
    'corsheaders',
    'recommendations',
    'rest_framework.authtoken', # Same as below
    'dj_rest_auth' # Added this as test for token based authentication
]

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar'] 

# Middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware") 

ROOT_URLCONF = 'pixelplaylist.urls' 

TEMPLATES = [ 
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates', 
        'DIRS': [], 
        'APP_DIRS': True, 
        'OPTIONS': {
            'context_processors': [ 
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pixelplaylist.wsgi.application' 

# Database
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", ""),
        conn_max_age=600, 
        conn_health_checks=True,
    )
}

# JWT setting
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny' if DEBUG else 'rest_framework.permissions.IsAuthenticated',
    ],
}

# Static files 
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'pixelplaylist-backend/static/' 


# Media files (if needed later)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
# Or use whitelist for prod:
# CORS_ALLOWED_ORIGINS = ["https://yourfrontend.app"] if not DEBUG else []

# Internal IPs for debug toolbar
if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"] # Allow local requests for debug toolbar

# Logging
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'WARNING',
                'class': 'logging.FileHandler',
                'filename': BASE_DIR / 'logs/django.log',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': True,
            }, 
        },
    }

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  

# Swagger settings for Auth testing:

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        },
    },
}
