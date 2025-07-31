"""
TPS V1.4 - Development Settings
Settings for local development environment
"""

import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-8g1@i!n4b#_*t5(!bc2dp7^5s3z6nmmx^vc#h$mle4=x45r8qf'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Development Database - SQLite for ease of development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Add debug toolbar for development - temporarily disabled
# if DEBUG:
#     INSTALLED_APPS += ['debug_toolbar']
#     MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
#     
#     # Extend INTERNAL_IPS for Tailwind development
#     INTERNAL_IPS += ['localhost', '127.0.0.1']

# Development email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable CSRF for development (if needed for API testing)
# CSRF_COOKIE_SECURE = False
# CSRF_COOKIE_HTTPONLY = False

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
