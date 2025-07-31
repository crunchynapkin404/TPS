# -*- coding: utf-8 -*-
"""
Custom locale formats for TPS V1.4
Forces 24-hour time format and DD/MM/YYYY date format system-wide
"""

# Date formats
DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
SHORT_DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
YEAR_MONTH_FORMAT = 'F Y'  # Month YYYY

# Time formats (24-hour)
TIME_FORMAT = 'H:i'  # HH:MM
SHORT_TIME_FORMAT = 'H:i'  # HH:MM

# DateTime formats
DATETIME_FORMAT = 'd/m/Y H:i'  # DD/MM/YYYY HH:MM
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'  # DD/MM/YYYY HH:MM

# Input formats for forms
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # DD/MM/YYYY (preferred)
    '%d-%m-%Y',  # DD-MM-YYYY
    '%d.%m.%Y',  # DD.MM.YYYY
    '%d %m %Y',  # DD MM YYYY
    '%Y-%m-%d',  # YYYY-MM-DD (ISO format fallback)
]

TIME_INPUT_FORMATS = [
    '%H:%M',     # HH:MM (24-hour, preferred)
    '%H:%M:%S',  # HH:MM:SS (24-hour)
    '%H.%M',     # HH.MM (24-hour)
    '%H-%M',     # HH-MM (24-hour)
]

DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M',     # DD/MM/YYYY HH:MM (preferred)
    '%d/%m/%Y %H:%M:%S',  # DD/MM/YYYY HH:MM:SS
    '%d-%m-%Y %H:%M',     # DD-MM-YYYY HH:MM
    '%d.%m.%Y %H:%M',     # DD.MM.YYYY HH:MM
    '%d %m %Y %H:%M',     # DD MM YYYY HH:MM
    '%Y-%m-%d %H:%M',     # YYYY-MM-DD HH:MM (ISO format)
    '%Y-%m-%d %H:%M:%S',  # YYYY-MM-DD HH:MM:SS (ISO format)
]

# Number formatting (European style)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3

# First day of week (Monday = 1, Sunday = 0)
FIRST_DAY_OF_WEEK = 1  # Monday
