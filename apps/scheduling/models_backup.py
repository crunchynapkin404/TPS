"""
TPS V1.4 - Scheduling Models
Shift templates, instances, and planning periods
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class ShiftCategory(models.Model):
    """
    Categories for organizing shift types (replaces VARCHAR choices)
    """
    CATEGORY_CHOICES = [
        ('WAAKDIENST', 'Waakdienst'),
        ('INCIDENT', 'Incident'),
        ('CHANGES', 'Changes'),
        ('PROJECTS', 'Projects'),
        ('OVERIG', 'Overig'),
    ]
    
    name = models.CharField(max_length=15, choices=CATEGORY_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex color for UI display"
    )
    
    # Business Rules
    max_weeks_per_year = models.PositiveIntegerField(
        help_text="Maximum weeks per year for this category"
    )
    hours_per_week = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Standard hours per week for this category"
    )
    min_gap_days = models.PositiveIntegerField(
        help_text="Minimum days between assignments in this category"
    )
    
    # Configuration
    requires_handover = models.BooleanField(default=False)
    allows_auto_assignment = models.BooleanField(default=True)
    priority_weight = models.PositiveIntegerField(
        default=1,
        help_text="Priority for automatic assignment (higher = more priority)"
    )
    
    class Meta:
        db_table = 'tps_shift_categories'
        ordering = ['name']
        
    def __str__(self):
        return self.display_name


class ShiftTemplate(models.Model):
    """
    Reusable shift definitions (replaces ShiftType)
    """
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        ShiftCategory,
        on_delete=models.CASCADE,
        related_name='shift_templates'
    )
    description = models.TextField(blank=True)
    
    # Timing
    start_time = models.TimeField(help_text="Standard start time")
    end_time = models.TimeField(help_text="Standard end time")
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Total duration in hours"
    )
    
    # Shift Characteristics
    is_overnight = models.BooleanField(
        default=False,
        help_text="Shift spans multiple days"
    )
    is_weekly_shift = models.BooleanField(
        default=False,
        help_text="Week-long assignment"
    )
    spans_weekend = models.BooleanField(
        default=False,
        help_text="Includes weekend days"
    )
    
    # Days Configuration
    days_of_week = models.JSONField(
        default=list,
        help_text="Array of weekday numbers (0=Monday, 6=Sunday)"
    )
    
    # Staffing Requirements
    engineers_required = models.PositiveIntegerField(default=1)
    backup_engineers = models.PositiveIntegerField(default=0)
    required_skills = models.JSONField(
        default=list,
        help_text="Array of required skill IDs"
    )
    
    # Pay Configuration
    base_pay_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00')
    )
    weekend_pay_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.25')
    )
    night_pay_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.15')
    )
    
    # Metadata
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_shift_templates'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_shift_templates'
        ordering = ['category__name', 'name']
        
    def __str__(self):
        return f"{self.category.display_name}: {self.name}"
    
    def get_pay_multiplier(self, is_weekend=False, is_night=False):
        """Calculate total pay multiplier"""
        multiplier = self.base_pay_multiplier
        if is_weekend:
            multiplier *= self.weekend_pay_multiplier
        if is_night:
            multiplier *= self.night_pay_multiplier
        return multiplier


class ShiftInstance(models.Model):
    """
    Actual shift occurrences (replaces Shift)
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('published', 'Published'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    # Unique identifier
    shift_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Template and Timing
    template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        related_name='instances'
    )
    date = models.DateField(help_text="Primary date for the shift")
    start_datetime = models.DateTimeField(help_text="Actual start date/time")
    end_datetime = models.DateTimeField(help_text="Actual end date/time")
    
    # Override Fields (if different from template)
    actual_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual duration if different from template"
    )
    location_override = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location if different from template"
    )
    
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Metadata
    is_emergency = models.BooleanField(
        default=False,
        help_text="Emergency or urgent shift"
    )
    requires_confirmation = models.BooleanField(
        default=True,
        help_text="Requires assignment confirmation"
    )
    
    # Planning Metadata
    planning_period = models.ForeignKey(
        'PlanningPeriod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shifts'
    )
    auto_generated = models.BooleanField(
        default=False,
        help_text="Created by automatic planning"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_shifts'
    )
    
    class Meta:
        db_table = 'tps_shift_instances'
        ordering = ['date', 'start_datetime']
        indexes = [
            models.Index(fields=['date', 'template']),
            models.Index(fields=['status', 'date']),
            models.Index(fields=['planning_period', 'date']),
        ]
        
    def __str__(self):
        return f"{self.template.name} - {self.date}"
    
    def get_actual_duration(self):
        """Get the actual duration, falling back to template duration"""
        return self.actual_duration_hours or self.template.duration_hours
    
    def is_in_past(self):
        """Check if shift is in the past"""
        return self.date < timezone.now().date()
    
    def can_be_modified(self):
        """Check if shift can still be modified"""
        return self.status in ['planned', 'published'] and not self.is_in_past()


class PlanningPeriod(models.Model):
    """
    Planning periods for organizing and tracking shift assignments
    """
    PERIOD_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom Period'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('planning', 'In Planning'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    
    # Period Dates
    start_date = models.DateField()
    end_date = models.DateField()
    planning_deadline = models.DateTimeField(
        help_text="Deadline for finalizing the planning"
    )
    publication_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the planning was published"
    )
    
    # Status and Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Configuration
    allows_auto_generation = models.BooleanField(
        default=True,
        help_text="Allow automatic shift generation for this period"
    )
    auto_generation_algorithm = models.CharField(
        max_length=20,
        choices=[
            ('balanced', 'Balanced Distribution'),
            ('sequential', 'Sequential Rotation'),
            ('custom', 'Custom Algorithm'),
        ],
        default='balanced'
    )
    
    # Metadata
    description = models.TextField(blank=True)
    planning_notes = models.TextField(blank=True)
    
    # Team/Department scope
    teams = models.ManyToManyField(
        'teams.Team',
        blank=True,
        related_name='planning_periods',
        help_text="Teams included in this planning period"
    )
    
    # Workflow tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_planning_periods'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_planning_periods'
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_planning_periods'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_planning_periods'
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def get_duration_days(self):
        """Get the duration of the planning period in days"""
        return (self.end_date - self.start_date).days + 1
    
    def is_active(self):
        """Check if the planning period is currently active"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def can_be_modified(self):
        """Check if the planning period can still be modified"""
        return self.status in ['draft', 'planning', 'review']
