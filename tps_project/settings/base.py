"""
TPS V1.4 - Base Settings
Common settings shared across all environments
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'tailwind',
    'theme',  # Tailwind theme app
    # 'channels',  # Will enable once needed
]

LOCAL_APPS = [
    # TPS Core Applications
    'apps.accounts',
    'apps.teams', 
    'apps.scheduling',
    'apps.assignments',
    'apps.leave_management',
    'apps.notifications',
    'core',
    'api',
    'frontend',  # Frontend templates and views
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ForceEuropeanFormatsMiddleware',  # Force EU date/time formats
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
                'core.context_processors.user_teams',
            ],
        },
    },
]

WSGI_APPLICATION = 'tps_project.wsgi.application'
# ASGI_APPLICATION = 'tps_project.asgi.application'  # Enable when needed

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en'  # Generic English
TIME_ZONE = 'Europe/Amsterdam'
USE_I18N = True
USE_L10N = False  # Disable localization to use our custom formats
USE_TZ = True

# Custom locale directory
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Format module path for custom formats
FORMAT_MODULE_PATH = [
    'locale',
]

# European Date/Time Formats
DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
TIME_FORMAT = 'H:i'    # 24-hour format
DATETIME_FORMAT = 'd/m/Y H:i'  # DD/MM/YYYY HH:MM
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'

# Input formats for forms
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',     # DD/MM/YYYY
    '%d-%m-%Y',     # DD-MM-YYYY
    '%d.%m.%Y',     # DD.MM.YYYY
    '%Y-%m-%d',     # YYYY-MM-DD (ISO format fallback)
]

TIME_INPUT_FORMATS = [
    '%H:%M',        # 24-hour format
    '%H:%M:%S',     # 24-hour format with seconds
]

DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M',
    '%d/%m/%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%d.%m.%Y %H:%M',
    '%Y-%m-%d %H:%M:%S',  # ISO format fallback
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'frontend' / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # European date/time formats for API
    'DATE_FORMAT': '%d/%m/%Y',
    'TIME_FORMAT': '%H:%M',
    'DATETIME_FORMAT': '%d/%m/%Y %H:%M',
    'DATE_INPUT_FORMATS': ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d'],
    'TIME_INPUT_FORMATS': ['%H:%M', '%H:%M:%S'],
    'DATETIME_INPUT_FORMATS': ['%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%Y-%m-%d %H:%M:%S'],
}

# Channels Configuration (commented for initial setup)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [('127.0.0.1', 6379)],
#         },
#     },
# }

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Tailwind CSS Configuration
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = [
    "127.0.0.1",
]

# TPS Business Configuration
TPS_CONFIG = {
    'MAX_WAAKDIENST_WEEKS_PER_YEAR': 8,
    'MAX_INCIDENT_WEEKS_PER_YEAR': 12,
    'MIN_GAP_WAAKDIENST_DAYS': 14,
    'MIN_GAP_INCIDENT_DAYS': 7,
    'WAAKDIENST_HOURS_PER_WEEK': 168,
    'INCIDENT_HOURS_PER_WEEK': 45,
}

# Logging Configuration
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
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'tps.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'tps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
