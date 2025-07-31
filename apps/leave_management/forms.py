"""
TPS V1.4 - Leave Management Forms
Django forms for leave request management
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta

from .models import LeaveType, LeaveRequest, RecurringLeave, LeaveBalance


class LeaveRequestForm(forms.ModelForm):
    """Form for creating and editing leave requests"""
    
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type', 'start_date', 'end_date', 'request_type',
            'start_time', 'end_time', 'hours_requested', 'reason'
        ]
        widgets = {
            'start_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'end_date': forms.DateInput(
                attrs={
                    'type': 'date', 
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'start_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'end_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'leave_type': forms.Select(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'request_type': forms.Select(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'hours_requested': forms.NumberInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'step': '0.5',
                    'min': '0.5',
                    'max': '8'
                }
            ),
            'reason': forms.Textarea(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'rows': 3,
                    'placeholder': 'Please provide a reason for your leave request...'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter active leave types
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        
        # Set minimum date to today
        self.fields['start_date'].widget.attrs['min'] = timezone.now().date().isoformat()
        self.fields['end_date'].widget.attrs['min'] = timezone.now().date().isoformat()
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        request_type = cleaned_data.get('request_type')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        hours_requested = cleaned_data.get('hours_requested')
        leave_type = cleaned_data.get('leave_type')
        
        # Validate date range
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError('End date cannot be before start date')
            
            if start_date < timezone.now().date():
                raise ValidationError('Cannot request leave for past dates')
        
        # Validate partial day requests
        if request_type == 'partial_day':
            if not start_time or not end_time:
                raise ValidationError('Start and end times are required for partial day requests')
            
            if start_time >= end_time:
                raise ValidationError('End time must be after start time')
        
        # Validate hourly requests
        if request_type == 'hourly':
            if not hours_requested:
                raise ValidationError('Hours requested is required for hourly leave')
            
            if hours_requested <= 0:
                raise ValidationError('Hours requested must be greater than 0')
        
        # Validate leave type specific rules
        if leave_type and start_date:
            # Check advance notice
            advance_days = (start_date - timezone.now().date()).days
            if advance_days < leave_type.min_advance_notice_days:
                raise ValidationError(
                    f'This leave type requires at least {leave_type.min_advance_notice_days} days advance notice'
                )
            
            # Check maximum days per request
            if leave_type.max_days_per_request and start_date and end_date:
                duration = (end_date - start_date).days + 1
                if duration > leave_type.max_days_per_request:
                    raise ValidationError(
                        f'This leave type allows maximum {leave_type.max_days_per_request} days per request'
                    )
        
        # Check for overlapping requests if user provided
        if self.user and start_date and end_date:
            overlapping = LeaveRequest.objects.filter(
                user=self.user,
                status__in=['approved', 'pending_manager', 'pending_hr', 'submitted']
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            for request in overlapping:
                if request.overlaps_with_period(start_date, end_date):
                    raise ValidationError(
                        f'This request overlaps with an existing request: {request.leave_type.name} '
                        f'({request.start_date} to {request.end_date})'
                    )
        
        return cleaned_data


class RecurringLeaveForm(forms.ModelForm):
    """Form for creating recurring leave patterns"""
    
    class Meta:
        model = RecurringLeave
        fields = [
            'name', 'leave_type', 'pattern_type', 'start_date', 'end_date',
            'day_of_week', 'day_of_month', 'interval_weeks',
            'is_full_day', 'start_time', 'end_time', 'hours_per_occurrence',
            'auto_create_requests', 'advance_creation_days', 'skip_holidays',
            'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'end_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'start_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'end_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'name': forms.TextInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'placeholder': 'e.g., Weekly Friday Afternoon Off'
                }
            ),
            'leave_type': forms.Select(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'pattern_type': forms.Select(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'day_of_week': forms.Select(
                choices=[
                    (None, 'Select day...'),
                    (0, 'Monday'),
                    (1, 'Tuesday'),
                    (2, 'Wednesday'),
                    (3, 'Thursday'),
                    (4, 'Friday'),
                    (5, 'Saturday'),
                    (6, 'Sunday'),
                ],
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
                }
            ),
            'day_of_month': forms.NumberInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'min': '1',
                    'max': '31'
                }
            ),
            'interval_weeks': forms.NumberInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'min': '1',
                    'max': '52'
                }
            ),
            'hours_per_occurrence': forms.NumberInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'step': '0.5',
                    'min': '0.5',
                    'max': '8'
                }
            ),
            'advance_creation_days': forms.NumberInput(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'min': '1',
                    'max': '365'
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                    'rows': 3,
                    'placeholder': 'Additional notes about this recurring pattern...'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active leave types
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        
        # Set minimum start date to today
        self.fields['start_date'].widget.attrs['min'] = timezone.now().date().isoformat()
    
    def clean(self):
        cleaned_data = super().clean()
        pattern_type = cleaned_data.get('pattern_type')
        day_of_week = cleaned_data.get('day_of_week')
        day_of_month = cleaned_data.get('day_of_month')
        interval_weeks = cleaned_data.get('interval_weeks')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_full_day = cleaned_data.get('is_full_day')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        hours_per_occurrence = cleaned_data.get('hours_per_occurrence')
        
        # Validate pattern-specific fields
        if pattern_type in ['weekly', 'bi_weekly'] and day_of_week is None:
            raise ValidationError('Day of week is required for weekly/bi-weekly patterns')
        
        if pattern_type == 'monthly' and day_of_month is None:
            raise ValidationError('Day of month is required for monthly patterns')
        
        if pattern_type == 'custom' and interval_weeks is None:
            raise ValidationError('Interval in weeks is required for custom patterns')
        
        # Validate date range
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError('End date cannot be before start date')
            
            if start_date < timezone.now().date():
                raise ValidationError('Cannot create recurring pattern for past dates')
        
        # Validate time fields for partial day patterns
        if not is_full_day:
            if not start_time or not end_time:
                raise ValidationError('Start and end times are required for partial day patterns')
            
            if start_time >= end_time:
                raise ValidationError('End time must be after start time')
            
            if not hours_per_occurrence:
                raise ValidationError('Hours per occurrence is required for partial day patterns')
        
        return cleaned_data


class LeaveApprovalForm(forms.Form):
    """Form for approving/declining leave requests"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('decline', 'Decline'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }
        )
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Optional notes about this decision...'
            }
        )
    )
    
    decline_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Please provide a reason for declining this request...'
            }
        )
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        decline_reason = cleaned_data.get('decline_reason')
        
        if action == 'decline' and not decline_reason:
            raise ValidationError('Decline reason is required when declining a request')
        
        return cleaned_data


class LeaveTypeFilterForm(forms.Form):
    """Form for filtering leave requests"""
    
    leave_type = forms.ModelChoiceField(
        queryset=LeaveType.objects.filter(is_active=True),
        required=False,
        empty_label="All Leave Types",
        widget=forms.Select(
            attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }
        )
    )
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending_manager', 'Pending Manager'),
        ('pending_hr', 'Pending HR'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }
        )
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }
        )
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }
        )
    )