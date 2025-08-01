"""
Production logging configuration for TPS
Structured logging with JSON format for production environments
"""
import os
import sys
from pathlib import Path

# Base directory for logs
LOG_DIR = Path(os.getenv('LOG_DIR', '/app/logs'))
LOG_DIR.mkdir(exist_ok=True)

# Log level from environment
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Log format from environment
LOG_FORMAT = os.getenv('LOG_FORMAT', 'json').lower()

# Django logging configuration
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
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
            'stream': sys.stdout,
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'error.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
        },
        'file_info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'tps.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'security.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 10,
            'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
        },
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'celery.log',
            'maxBytes': 20 * 1024 * 1024,  # 20MB
            'backupCount': 5,
            'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
        },
        'access_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'access.log',
            'maxBytes': 100 * 1024 * 1024,  # 100MB
            'backupCount': 5,
            'formatter': 'json' if LOG_FORMAT == 'json' else 'simple',
        },
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console', 'file_info'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file_info'] if LOG_LEVEL == 'DEBUG' else [],
            'level': 'DEBUG',
            'propagate': False,
        },
        'tps': {
            'handlers': ['console', 'file_info'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'tps.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'tps.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['celery_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.error': {
            'handlers': ['file_error', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Production-specific logging adjustments
if os.getenv('ENVIRONMENT') == 'production':
    # Reduce console logging in production
    LOGGING['handlers']['console']['level'] = 'WARNING'
    
    # Add syslog handler for production
    LOGGING['handlers']['syslog'] = {
        'level': 'INFO',
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'formatter': 'json' if LOG_FORMAT == 'json' else 'verbose',
        'facility': 'local0',
    }
    
    # Add syslog to root and main loggers
    for logger_name in ['root', 'django', 'tps']:
        if logger_name in LOGGING['loggers']:
            LOGGING['loggers'][logger_name]['handlers'].append('syslog')
        elif logger_name == 'root':
            LOGGING['root']['handlers'].append('syslog')

# Custom log record factory for additional context
def add_context_factory(old_factory):
    def new_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.hostname = os.getenv('HOSTNAME', 'unknown')
        record.service = 'tps'
        record.environment = os.getenv('ENVIRONMENT', 'unknown')
        return record
    return new_factory

# Apply custom factory
import logging
logging.setLogRecordFactory(add_context_factory(logging.getLogRecordFactory()))