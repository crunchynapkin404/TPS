"""
Test date and time formatting settings
"""
from django.core.management.base import BaseCommand
from django.utils import formats, timezone
from datetime import datetime, date, time


class Command(BaseCommand):
    help = 'Test date and time formatting to verify EU format settings'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing date and time formatting...'))
        
        # Test data
        test_date = date(2025, 7, 30)  # July 30, 2025
        test_time = time(14, 30)  # 2:30 PM
        test_datetime = datetime(2025, 7, 30, 14, 30)  # July 30, 2025 2:30 PM
        
        self.stdout.write('\n--- DATE FORMATTING TESTS ---')
        self.stdout.write(f'Test Date: {test_date} (YYYY-MM-DD)')
        self.stdout.write(f'Date Format: {formats.date_format(test_date)}')
        self.stdout.write(f'Short Date Format: {formats.date_format(test_date, "SHORT_DATE_FORMAT")}')
        
        self.stdout.write('\n--- TIME FORMATTING TESTS ---')
        self.stdout.write(f'Test Time: {test_time} (24-hour)')
        self.stdout.write(f'Time Format: {formats.time_format(test_time)}')
        
        self.stdout.write('\n--- DATETIME FORMATTING TESTS ---')
        self.stdout.write(f'Test DateTime: {test_datetime} (ISO format)')
        self.stdout.write(f'DateTime Format: {formats.date_format(test_datetime, "DATETIME_FORMAT")}')
        self.stdout.write(f'Short DateTime Format: {formats.date_format(test_datetime, "SHORT_DATETIME_FORMAT")}')
        
        self.stdout.write('\n--- FORMAT SETTINGS ---')
        self.stdout.write(f'DATE_FORMAT: {formats.get_format("DATE_FORMAT")}')
        self.stdout.write(f'TIME_FORMAT: {formats.get_format("TIME_FORMAT")}')
        self.stdout.write(f'DATETIME_FORMAT: {formats.get_format("DATETIME_FORMAT")}')
        self.stdout.write(f'DATE_INPUT_FORMATS: {formats.get_format("DATE_INPUT_FORMATS")}')
        self.stdout.write(f'TIME_INPUT_FORMATS: {formats.get_format("TIME_INPUT_FORMATS")}')
        
        self.stdout.write('\n--- LOCALE SETTINGS ---')
        from django.conf import settings
        self.stdout.write(f'LANGUAGE_CODE: {settings.LANGUAGE_CODE}')
        self.stdout.write(f'USE_I18N: {settings.USE_I18N}')
        self.stdout.write(f'USE_TZ: {settings.USE_TZ}')
        if hasattr(settings, 'DECIMAL_SEPARATOR'):
            self.stdout.write(f'DECIMAL_SEPARATOR: {settings.DECIMAL_SEPARATOR}')
        if hasattr(settings, 'THOUSAND_SEPARATOR'):
            self.stdout.write(f'THOUSAND_SEPARATOR: {settings.THOUSAND_SEPARATOR}')
        
        self.stdout.write(self.style.SUCCESS('\nFormatting test completed!'))
