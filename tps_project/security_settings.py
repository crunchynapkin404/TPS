"""
TPS V1.4 - Security Settings
Production security configuration and validation
"""

import os
import warnings
from django.core.management.utils import get_random_secret_key


def validate_security_settings():
    """
    Validate critical security settings and provide warnings
    """
    security_issues = []
    
    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key:
        security_issues.append("CRITICAL: SECRET_KEY environment variable not set")
    elif secret_key.startswith('django-insecure-'):
        security_issues.append("CRITICAL: SECRET_KEY appears to be a default Django development key")
    elif len(secret_key) < 50:
        security_issues.append("WARNING: SECRET_KEY should be at least 50 characters long")
    
    # Check DEBUG setting
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    environment = os.getenv('ENVIRONMENT', 'production')
    if debug and environment == 'production':
        security_issues.append("CRITICAL: DEBUG=True should never be used in production")
    
    # Check database password
    db_password = os.getenv('DB_PASSWORD', '')
    if environment == 'production' and not db_password:
        security_issues.append("WARNING: Database password not set for production environment")
    
    # Check admin password
    admin_password = os.getenv('ADMIN_PASSWORD', '')
    if admin_password in ['admin123', 'password123', 'change-this-secure-password']:
        security_issues.append("CRITICAL: Admin password appears to be a default/weak password")
    
    # Check ALLOWED_HOSTS for production
    allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]')
    if environment == 'production' and 'localhost' in allowed_hosts:
        security_issues.append("WARNING: Production ALLOWED_HOSTS should not include localhost")
    
    return security_issues


def get_security_settings():
    """
    Return security-focused Django settings
    """
    environment = os.getenv('ENVIRONMENT', 'production')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Base security settings
    security_settings = {
        # HTTPS Security
        'SECURE_SSL_REDIRECT': not debug,
        'SECURE_PROXY_SSL_HEADER': ('HTTP_X_FORWARDED_PROTO', 'https'),
        'SECURE_HSTS_SECONDS': 31536000 if not debug else 0,  # 1 year
        'SECURE_HSTS_INCLUDE_SUBDOMAINS': True,
        'SECURE_HSTS_PRELOAD': True,
        'SECURE_CONTENT_TYPE_NOSNIFF': True,
        'SECURE_BROWSER_XSS_FILTER': True,
        'SECURE_REFERRER_POLICY': 'strict-origin-when-cross-origin',
        
        # Cookie Security
        'SESSION_COOKIE_SECURE': not debug,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_AGE': 3600,  # 1 hour
        'SESSION_EXPIRE_AT_BROWSER_CLOSE': True,
        'SESSION_SAVE_EVERY_REQUEST': True,
        
        # CSRF Security
        'CSRF_COOKIE_SECURE': not debug,
        'CSRF_COOKIE_HTTPONLY': True,
        'CSRF_COOKIE_SAMESITE': 'Lax',
        'CSRF_USE_SESSIONS': True,
        
        # Security Headers
        'X_FRAME_OPTIONS': 'DENY',
        
        # Password Validation
        'AUTH_PASSWORD_VALIDATORS': [
            {
                'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
                'OPTIONS': {
                    'min_length': 12,
                }
            },
            {
                'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
            },
        ],
        
        # Logging Security
        'LOGGING': {
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
            'filters': {
                'require_debug_false': {
                    '()': 'django.utils.log.RequireDebugFalse',
                },
            },
            'handlers': {
                'file': {
                    'level': 'WARNING',
                    'class': 'logging.FileHandler',
                    'filename': '/var/log/tps/security.log' if environment == 'production' else 'security.log',
                    'formatter': 'verbose',
                    'filters': ['require_debug_false'],
                },
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple',
                },
            },
            'loggers': {
                'django.security': {
                    'handlers': ['file', 'console'],
                    'level': 'WARNING',
                    'propagate': True,
                },
                'tps.security': {
                    'handlers': ['file', 'console'],
                    'level': 'INFO',
                    'propagate': True,
                },
            },
        },
    }
    
    # Development overrides
    if debug:
        security_settings.update({
            'SECURE_SSL_REDIRECT': False,
            'SECURE_HSTS_SECONDS': 0,
            'SESSION_COOKIE_SECURE': False,
            'CSRF_COOKIE_SECURE': False,
        })
    
    return security_settings


def get_cors_settings():
    """
    Return CORS settings for API security
    """
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    allowed_origins = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    
    if debug:
        # Development CORS settings
        return {
            'CORS_ALLOW_ALL_ORIGINS': True,
            'CORS_ALLOW_CREDENTIALS': True,
            'CORS_ALLOWED_HEADERS': [
                'accept',
                'accept-encoding',
                'authorization',
                'content-type',
                'dnt',
                'origin',
                'user-agent',
                'x-csrftoken',
                'x-requested-with',
            ],
        }
    else:
        # Production CORS settings
        return {
            'CORS_ALLOW_ALL_ORIGINS': False,
            'CORS_ALLOWED_ORIGINS': [origin.strip() for origin in allowed_origins if origin.strip()],
            'CORS_ALLOW_CREDENTIALS': True,
            'CORS_ALLOWED_HEADERS': [
                'accept',
                'accept-encoding',
                'authorization',
                'content-type',
                'origin',
                'x-csrftoken',
                'x-requested-with',
            ],
            'CORS_ALLOWED_METHODS': [
                'DELETE',
                'GET',
                'OPTIONS',
                'PATCH',
                'POST',
                'PUT',
            ],
            'CORS_PREFLIGHT_MAX_AGE': 86400,
        }


def generate_secure_secret_key():
    """
    Generate a secure SECRET_KEY for production use
    """
    return get_random_secret_key()


# Security middleware configuration
SECURITY_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add CORS middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]