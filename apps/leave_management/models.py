"""
TPS V1.4 - Leave Management Models
Enhanced leave requests with recurring patterns and approval workflows
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from datetime import date, timedelta


class LeaveType(models.Model):
    """
    Types of leave that can be requested
    """
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    
    # Leave characteristics
    is_paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    requires_manager_approval = models.BooleanField(default=True)
    requires_hr_approval = models.BooleanField(default=False)
    
    # Limits and rules
    max_days_per_request = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum days that can be requested at once"
    )
    max_days_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum days per calendar year"
    )
    min_advance_notice_days = models.PositiveIntegerField(
        default=7,
        help_text="Minimum days advance notice required"
    )
    
    # Configuration
    affects_shift_planning = models.BooleanField(
        default=True,
        help_text="Whether this leave type affects shift assignments"
    )
    color = models.CharField(
        max_length=7,
        default='#10B981',
        help_text="Color for calendar display"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tps_leave_types'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """
    Individual leave requests with approval workflow
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending_manager', 'Pending Manager Approval'),
        ('pending_hr', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    REQUEST_TYPES = [
        ('full_day', 'Full Day'),
        ('partial_day', 'Partial Day'),
        ('hourly', 'Hourly'),
    ]
    
    # Unique identifier
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Core request details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    
    # Request timing
    start_date = models.DateField()
    end_date = models.DateField()
    request_type = models.CharField(
        max_length=12,
        choices=REQUEST_TYPES,
        default='full_day'
    )
    
    # For partial/hourly requests
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for partial day requests"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for partial day requests"
    )
    hours_requested = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hours requested for hourly leave"
    )
    
    # Request details
    reason = models.TextField(help_text="Reason for leave request")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Workflow tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    manager_reviewed_at = models.DateTimeField(null=True, blank=True)
    manager_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manager_leave_reviews'
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_leave_reviews'
    )
    
    # Response details
    manager_notes = models.TextField(blank=True)
    hr_notes = models.TextField(blank=True)
    decline_reason = models.TextField(blank=True)
    
    # Impact assessment
    affects_critical_shifts = models.BooleanField(
        default=False,
        help_text="Leave affects critical shift coverage"
    )
    impact_notes = models.TextField(
        blank=True,
        help_text="Notes about planning impact"
    )
    
    # Recurring leave relationship
    recurring_leave = models.ForeignKey(
        'RecurringLeave',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instances'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_leave_requests'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['user', 'start_date']),
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['leave_type', 'start_date']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.leave_type.name} ({self.start_date})"
    
    def get_duration_days(self):
        """Calculate duration in days"""
        return (self.end_date - self.start_date).days + 1
    
    def overlaps_with_date(self, check_date):
        """Check if leave request overlaps with a specific date"""
        return self.start_date <= check_date <= self.end_date
    
    def overlaps_with_period(self, start_date, end_date):
        """Check if leave request overlaps with a date range"""
        return not (self.end_date < start_date or self.start_date > end_date)
    
    def can_be_cancelled(self):
        """Check if request can be cancelled"""
        return (
            self.status in ['draft', 'submitted', 'pending_manager', 'pending_hr', 'approved'] and
            self.start_date > timezone.now().date()
        )
    
    def requires_manager_approval(self):
        """Check if manager approval is required"""
        return self.leave_type.requires_manager_approval
    
    def requires_hr_approval(self):
        """Check if HR approval is required"""
        return self.leave_type.requires_hr_approval
    
    def is_sufficient_notice(self):
        """Check if sufficient advance notice was given"""
        notice_days = (self.start_date - timezone.now().date()).days
        return notice_days >= self.leave_type.min_advance_notice_days


class RecurringLeave(models.Model):
    """
    Recurring leave patterns (e.g., every Friday, monthly medical appointments)
    """
    PATTERN_TYPES = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Pattern'),
    ]
    
    # Unique identifier
    pattern_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Pattern details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_leave_patterns'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='recurring_patterns'
    )
    
    # Pattern configuration
    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for the pattern"
    )
    pattern_type = models.CharField(max_length=20, choices=PATTERN_TYPES)
    
    # Timing
    start_date = models.DateField(help_text="When the pattern starts")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the pattern ends (null = indefinite)"
    )
    
    # Pattern details
    day_of_week = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Day of week (0=Monday, 6=Sunday) for weekly patterns"
    )
    day_of_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day of month for monthly patterns"
    )
    interval_weeks = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Interval in weeks for custom patterns"
    )
    
    # Time details (for partial day patterns)
    is_full_day = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    hours_per_occurrence = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Configuration
    auto_create_requests = models.BooleanField(
        default=True,
        help_text="Automatically create leave requests for this pattern"
    )
    advance_creation_days = models.PositiveIntegerField(
        default=30,
        help_text="How many days in advance to create requests"
    )
    skip_holidays = models.BooleanField(
        default=True,
        help_text="Skip pattern occurrences on holidays"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_generated_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date for which requests were generated"
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_recurring_leave'
        ordering = ['user__last_name', 'name']
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.name}"
    
    def get_next_occurrence(self, from_date=None):
        """Get the next occurrence date based on the pattern"""
        if from_date is None:
            from_date = timezone.now().date()
        
        if self.pattern_type == 'weekly' and self.day_of_week is not None:
            days_ahead = self.day_of_week - from_date.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return from_date + timedelta(days=days_ahead)
        
        # Additional pattern logic would be implemented here
        return None
    
    def should_create_request(self, target_date):
        """Check if a request should be created for the target date"""
        if not self.auto_create_requests or not self.is_active:
            return False
        
        if self.end_date and target_date > self.end_date:
            return False
        
        if target_date < self.start_date:
            return False
        
        # Check if already created
        if LeaveRequest.objects.filter(
            recurring_leave=self,
            start_date=target_date
        ).exists():
            return False
        
        return True


class LeaveBalance(models.Model):
    """
    Track leave balances for users by leave type and year
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    year = models.PositiveIntegerField()
    
    # Balance tracking
    annual_allocation = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Total days/hours allocated for the year"
    )
    carried_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Days/hours carried forward from previous year"
    )
    used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Days/hours used so far"
    )
    pending = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Days/hours in pending requests"
    )
    
    # Audit
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_leave_balances'
        unique_together = ['user', 'leave_type', 'year']
        ordering = ['year', 'user__last_name']
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.leave_type.name} {self.year}"
    
    @property
    def total_available(self):
        """Calculate total available balance"""
        return self.annual_allocation + self.carried_forward
    
    @property
    def remaining(self):
        """Calculate remaining balance"""
        return self.total_available - self.used - self.pending
    
    def can_request(self, days_requested):
        """Check if user can request the specified days"""
        return self.remaining >= days_requested
