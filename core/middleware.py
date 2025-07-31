"""
Middleware to force European date/time formats
"""
from django.utils import formats


class ForceEuropeanFormatsMiddleware:
    """Middleware that forces European date/time formats."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Monkey patch the format functions to return our formats
        self._patch_formats()
        response = self.get_response(request)
        return response
    
    def _patch_formats(self):
        """Patch Django's format system to use European formats."""
        # Store original functions if not already stored
        if not hasattr(self, '_original_get_format'):
            self._original_get_format = formats.get_format
            
        # Override get_format function
        def custom_get_format(format_type, lang=None, use_l10n=None):
            format_map = {
                'DATE_FORMAT': 'd/m/Y',
                'TIME_FORMAT': 'H:i',
                'DATETIME_FORMAT': 'd/m/Y H:i',
                'SHORT_DATE_FORMAT': 'd/m/Y',
                'SHORT_DATETIME_FORMAT': 'd/m/Y H:i',
            }
            
            if format_type in format_map:
                return format_map[format_type]
            
            # Fall back to original function for other formats
            return self._original_get_format(format_type, lang, use_l10n)
        
        # Apply the patch
        formats.get_format = custom_get_format
