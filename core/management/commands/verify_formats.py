"""
Management command to verify European date/time formatting is working
"""
from django.core.management.base import BaseCommand
from django.utils import formats
from django.template import Template, Context
from datetime import date, time, datetime


class Command(BaseCommand):
    help = 'Verify European date/time formatting is working correctly'

    def handle(self, *args, **options):
        self.stdout.write("Testing European date/time formatting...")
        self.stdout.write("=" * 50)
        
        # Test data
        test_date = date(2025, 7, 30)
        test_time = time(14, 30)
        test_datetime = datetime(2025, 7, 30, 14, 30)
        
        # Test format functions
        self.stdout.write("\n--- FORMAT FUNCTIONS ---")
        self.stdout.write(f"Date format: {formats.date_format(test_date)}")
        self.stdout.write(f"Time format: {formats.time_format(test_time)}")
        self.stdout.write(f"DateTime format: {formats.date_format(test_datetime, 'DATETIME_FORMAT')}")
        
        # Test get_format
        self.stdout.write("\n--- FORMAT SETTINGS ---")
        self.stdout.write(f"DATE_FORMAT: {formats.get_format('DATE_FORMAT')}")
        self.stdout.write(f"TIME_FORMAT: {formats.get_format('TIME_FORMAT')}")
        self.stdout.write(f"DATETIME_FORMAT: {formats.get_format('DATETIME_FORMAT')}")
        
        # Test template rendering
        self.stdout.write("\n--- TEMPLATE RENDERING ---")
        template_str = """
        {% load l10n %}
        Date: {{ test_date }}
        Time: {{ test_time }}
        DateTime: {{ test_datetime }}
        Date Localized: {{ test_date|date:"d/m/Y" }}
        Time Localized: {{ test_time|time:"H:i" }}
        """
        
        template = Template(template_str)
        context = Context({
            'test_date': test_date,
            'test_time': test_time,
            'test_datetime': test_datetime,
        })
        
        rendered = template.render(context)
        self.stdout.write(rendered.strip())
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("✅ European formatting verification completed!")
        
        # Verify expected formats
        expected_date = "30/07/2025"
        expected_time = "14:30"
        actual_date = formats.date_format(test_date)
        actual_time = formats.time_format(test_time)
        
        if actual_date == expected_date and actual_time == expected_time:
            self.stdout.write(self.style.SUCCESS("✅ All formats are correct!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  Format mismatch - Expected: {expected_date} {expected_time}, Got: {actual_date} {actual_time}"))
