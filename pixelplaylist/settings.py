import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import dj_database_url

# Environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Detect environment (dev or prod)
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")

IS_PRODUCTION = (
    ENVIRONMENT == "production" or
    os.getenv("RENDER") or 
    not os.getenv("DATABASE_URL", "").startswith("sqlite")
)
DEBUG = not IS_PRODUCTION

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
        conn_max_age=30, # Reduced to prevent timeout issues
        conn_health_checks=True
    )
}

# DB retry config for prod

if not DEBUG:
    DATABASES['default']['OPTIONS'] = DATABASES['default'].get('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        'connect_timeout': 10,  # Reduced timeout for production
        'options': '-c default_transaction_isolation=serializable' # Use serializable isolation level for better consistency
    })

# JWT setting
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,  # Allow rotation of refresh tokens
    "BLACKLIST_AFTER_ROTATION": True,  # Blacklist old refresh tokens after rotation
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
]

# Custom auth backend for email and username login
AUTHENTICATION_BACKENDS = [
    'recommendations.backends.EmailBackend',  # Try email first
    'django.contrib.auth.backends.ModelBackend',  # Fallback to username
]

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Allow anonymous access by default
    ],
}

# Static files 
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static' 


# Media files (if needed later)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOWED_ORIGINS = [
        "https://pixelplaylist.onrender.com",
        "https://pixelplaylist-6t3b1t5kf-kims-projects-6e7fcba5.vercel.app/",
        "https://pixelplaylist.vercel.app",  
    ]
    CORS_ALLOW_CREDENTIALS = True
    
# CORS methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
    
# CSRF trusted origins:
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "https://pixelplaylist.onrender.com",
        "https://pixelplaylist-6t3b1t5kf-kims-projects-6e7fcba5.vercel.app/",  # Replace with actual frontend URL
        "https://pixelplaylist.vercel.app",  #
    ]

# Internal IPs for debug toolbar
if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"] # Allow local requests for debug toolbar

# Logging configuration - Updated for prod deployment
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        # Only use file handler in development when logs directory exists
        'file': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',  # Changed from FileHandler to StreamHandler to address render issue
            'formatter': 'verbose',
        } if DEBUG else {
            'level': 'ERROR', 
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'recommendations': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
    
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

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
