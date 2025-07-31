"""
Temporary simple settings for testing Django setup
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-8g1@i!n4b#_*t5(!bc2dp7^5s3z6nmmx^vc#h$mle4=x45r8qf'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-gb'  # Use British English for DD/MM/YYYY format
TIME_ZONE = 'Europe/Amsterdam'
USE_I18N = True
USE_L10N = True  # Enable localization
USE_TZ = True

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
}
