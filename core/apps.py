from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Override Django formats when the app is ready."""
        # Force European date/time formats
        settings.DATE_FORMAT = 'd/m/Y'
        settings.TIME_FORMAT = 'H:i'
        settings.DATETIME_FORMAT = 'd/m/Y H:i'
        settings.SHORT_DATE_FORMAT = 'd/m/Y'
        settings.SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
