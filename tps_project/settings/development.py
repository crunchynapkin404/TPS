"""
TPS V1.4 - Development Settings
Settings for local development environment
"""

import os
from .base import *

# Development requires environment variables too for security
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    # Only for development - provide a warning
    SECRET_KEY = 'django-insecure-dev-only-change-in-env-file'
    print("WARNING: Using default SECRET_KEY. Please set SECRET_KEY in your .env file!")

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

# Development email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable CSRF for development (if needed for API testing)
# CSRF_COOKIE_SECURE = False
# CSRF_COOKIE_HTTPONLY = False

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
