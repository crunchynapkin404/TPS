"""
TPS V1.4 - Django Settings
Enhanced settings with custom User model and TPS apps
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'channels',
    
    # TPS Applications
    'apps.accounts',
    'apps.teams',
    'apps.scheduling',
    'apps.assignments',
    'apps.leave_management',
    'apps.notifications',
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tps_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'templates'],
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

WSGI_APPLICATION = 'tps_project.wsgi.application'
ASGI_APPLICATION = 'tps_project.asgi.application'

# Channel Layers Configuration for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))],
        },
    },
}

# Fallback to in-memory channel layer if Redis is not available
try:
    import redis
    import channels_redis
except ImportError:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

LANGUAGE_CODE = 'en-gb'  # Use British English for DD/MM/YYYY format
TIME_ZONE = 'Europe/Amsterdam'
USE_I18N = True
USE_L10N = True  # Enable localization
USE_TZ = True

# Custom locale directory
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Format module path for custom formats
FORMAT_MODULE_PATH = [
    'locale',
]

# Custom date and time formats (24-hour time, DD/MM/YYYY dates)
DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
SHORT_DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
DATETIME_FORMAT = 'd/m/Y H:i'  # DD/MM/YYYY HH:MM (24-hour)
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'  # DD/MM/YYYY HH:MM (24-hour)
TIME_FORMAT = 'H:i'  # HH:MM (24-hour)

# Input formats for forms (accept various formats but prefer 24-hour and DD/MM/YYYY)
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # DD/MM/YYYY (preferred)
    '%d-%m-%Y',  # DD-MM-YYYY
    '%d.%m.%Y',  # DD.MM.YYYY
    '%Y-%m-%d',  # YYYY-MM-DD (ISO format)
]

TIME_INPUT_FORMATS = [
    '%H:%M',     # HH:MM (24-hour, preferred)
    '%H:%M:%S',  # HH:MM:SS (24-hour)
    '%H.%M',     # HH.MM (24-hour)
]

DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M',     # DD/MM/YYYY HH:MM (preferred)
    '%d/%m/%Y %H:%M:%S',  # DD/MM/YYYY HH:MM:SS
    '%d-%m-%Y %H:%M',     # DD-MM-YYYY HH:MM
    '%d.%m.%Y %H:%M',     # DD.MM.YYYY HH:MM
    '%Y-%m-%d %H:%M',     # YYYY-MM-DD HH:MM (ISO format)
    '%Y-%m-%d %H:%M:%S',  # YYYY-MM-DD HH:MM:SS (ISO format)
]

# Force specific number formatting
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
USE_THOUSAND_SEPARATOR = True

# First day of week (Monday)
FIRST_DAY_OF_WEEK = 1

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'frontend' / 'static',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Consistent date/time formatting for API
    'DATE_FORMAT': '%d/%m/%Y',  # DD/MM/YYYY
    'DATETIME_FORMAT': '%d/%m/%Y %H:%M',  # DD/MM/YYYY HH:MM (24-hour)
    'TIME_FORMAT': '%H:%M',  # HH:MM (24-hour)
    'DATE_INPUT_FORMATS': [
        '%d/%m/%Y',  # DD/MM/YYYY (preferred)
        '%d-%m-%Y',  # DD-MM-YYYY
        '%d.%m.%Y',  # DD.MM.YYYY
        '%Y-%m-%d',  # YYYY-MM-DD (ISO format)
    ],
    'TIME_INPUT_FORMATS': [
        '%H:%M',     # HH:MM (24-hour, preferred)
        '%H:%M:%S',  # HH:MM:SS (24-hour)
    ],
    'DATETIME_INPUT_FORMATS': [
        '%d/%m/%Y %H:%M',     # DD/MM/YYYY HH:MM (preferred)
        '%d/%m/%Y %H:%M:%S',  # DD/MM/YYYY HH:MM:SS
        '%d-%m-%Y %H:%M',     # DD-MM-YYYY HH:MM
        '%d.%m.%Y %H:%M',     # DD.MM.YYYY HH:MM
        '%Y-%m-%d %H:%M',     # YYYY-MM-DD HH:MM (ISO format)
        '%Y-%m-%d %H:%M:%S',  # YYYY-MM-DD HH:MM:SS (ISO format)
    ],
}

# TPS Business Configuration
TPS_CONFIG = {
    'MAX_WAAKDIENST_WEEKS_PER_YEAR': int(os.getenv('TPS_MAX_WAAKDIENST_WEEKS_PER_YEAR', '8')),
    'MAX_INCIDENT_WEEKS_PER_YEAR': int(os.getenv('TPS_MAX_INCIDENT_WEEKS_PER_YEAR', '12')),
    'MIN_GAP_WAAKDIENST_DAYS': int(os.getenv('TPS_MIN_GAP_WAAKDIENST_DAYS', '14')),
    'MIN_GAP_INCIDENT_DAYS': int(os.getenv('TPS_MIN_GAP_INCIDENT_DAYS', '7')),
    'WAAKDIENST_HOURS_PER_WEEK': int(os.getenv('TPS_WAAKDIENST_HOURS_PER_WEEK', '168')),
    'INCIDENT_HOURS_PER_WEEK': int(os.getenv('TPS_INCIDENT_HOURS_PER_WEEK', '45')),
}

# Authentication Settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Local Apps
LOCAL_APPS = [
    'core',
    'api',
    'frontend',
]

# Third-party Apps
THIRD_PARTY_APPS = [
    'rest_framework',
    'tailwind',
    'theme',
]

# Complete installed apps list
INSTALLED_APPS += THIRD_PARTY_APPS + LOCAL_APPS

# Development-specific settings (only for local dev)
if DEBUG and False:  # Temporarily disabled for clean UI
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1', 'localhost']
