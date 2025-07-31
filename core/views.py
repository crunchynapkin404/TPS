from django.http import JsonResponse
from django.utils import formats
from datetime import date, time, datetime


def test_formats_view(request):
    """Test view to check date/time formatting."""
    test_date = date(2025, 7, 30)
    test_time = time(14, 30)
    test_datetime = datetime(2025, 7, 30, 14, 30)
    
    return JsonResponse({
        'date_format': formats.get_format('DATE_FORMAT'),
        'time_format': formats.get_format('TIME_FORMAT'),
        'datetime_format': formats.get_format('DATETIME_FORMAT'),
        'formatted_date': formats.date_format(test_date),
        'formatted_time': formats.time_format(test_time),
        'formatted_datetime': formats.date_format(test_datetime, 'DATETIME_FORMAT'),
    })
