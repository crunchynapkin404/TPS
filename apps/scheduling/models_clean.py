"""
TPS V1.4 - Clean Scheduling Models
Shift planning and assignment with proper Django relationships (no JSONField abuse)
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from core.models import Status, Priority, Skill, SkillCategory, ShiftCategory
from apps.teams.models import Team


class ShiftTemplate(models.Model):
    """
    Clean shift template model (no JSONField abuse)
    Reusable shift definitions with proper relationships
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
    
    # Staffing Requirements
    engineers_required = models.PositiveIntegerField(default=1)
    backup_engineers = models.PositiveIntegerField(default=0)
    
    # Required skills (proper many-to-many instead of JSONField)
    required_skills = models.ManyToManyField(
        Skill,
        through='ShiftTemplateSkillRequirement',
        related_name='required_by_templates'
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
        default=Decimal('1.50')
    )
    night_pay_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.25')
    )
    
    # Template status
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='shift_templates'
    )
    
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='shift_templates'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_shift_templates'
    )
    
    class Meta:
        db_table = 'tps_shift_templates'
        ordering = ['category__name', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_weekly_shift']),
        ]
        
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_total_pay_multiplier(self, is_weekend=False, is_night=False):
        """Calculate total pay multiplier based on conditions"""
        multiplier = self.base_pay_multiplier
        if is_weekend:
            multiplier *= self.weekend_pay_multiplier
        if is_night:
            multiplier *= self.night_pay_multiplier
        return multiplier


class ShiftTemplateDayOfWeek(models.Model):
    """
    Days of week for shift templates (replacing JSONField days_of_week)
    """
    template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        related_name='template_days'
    )
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    
    # Day-specific overrides
    start_time_override = models.TimeField(null=True, blank=True)
    end_time_override = models.TimeField(null=True, blank=True)
    duration_override = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Staffing overrides for this day
    engineers_required_override = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'tps_shift_template_days'
        unique_together = ['template', 'day_of_week']
        indexes = [
            models.Index(fields=['template']),
            models.Index(fields=['day_of_week']),
        ]
        
    def __str__(self):
        day_names = dict(self.DAYS_OF_WEEK)
        return f"{self.template.name} - {day_names.get(self.day_of_week, 'Unknown')}"


class ShiftTemplateSkillRequirement(models.Model):
    """
    Skill requirements for shift templates (replacing JSONField required_skills)
    """
    template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        related_name='template_skill_requirements'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='template_requirements'
    )
    
    # Requirement details
    REQUIREMENT_TYPES = [
        ('mandatory', 'Mandatory'),
        ('preferred', 'Preferred'),
        ('optional', 'Optional'),
        ('one_of_group', 'One of Group'),
    ]
    
    requirement_type = models.CharField(
        max_length=20,
        choices=REQUIREMENT_TYPES,
        default='mandatory'
    )
    
    # Minimum proficiency required
    MINIMUM_PROFICIENCY = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    minimum_proficiency = models.CharField(
        max_length=20,
        choices=MINIMUM_PROFICIENCY,
        default='intermediate'
    )
    
    # Group for "one_of_group" requirements
    skill_group = models.CharField(
        max_length=50,
        blank=True,
        help_text="Group name for 'one of group' requirements"
    )
    
    # Priority for this requirement
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='template_skill_requirements'
    )
    
    class Meta:
        db_table = 'tps_shift_template_skill_requirements'
        unique_together = ['template', 'skill']
        indexes = [
            models.Index(fields=['template']),
            models.Index(fields=['skill']),
            models.Index(fields=['requirement_type']),
            models.Index(fields=['minimum_proficiency']),
        ]
        
    def __str__(self):
        return f"{self.template.name} - {self.skill.name} ({self.requirement_type})"


class ShiftInstance(models.Model):
    """
    Clean shift instance model with proper status relationships
    Actual shift occurrences
    """
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
    
    # Status using foundation model
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='shift_instances'
    )
    
    # Priority for this instance
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='shift_instances'
    )
    
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
    
    # Assignment tracking
    assigned_engineers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ShiftAssignment',
        related_name='assigned_shifts'
    )
    
    # Planning context
    planning_period = models.ForeignKey(
        'PlanningPeriod',
        on_delete=models.CASCADE,
        related_name='shift_instances',
        null=True,
        blank=True
    )
    
    # Notes and tracking
    shift_notes = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_shift_instances'
    )
    
    class Meta:
        db_table = 'tps_shift_instances'
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['start_datetime', 'end_datetime']),
            models.Index(fields=['template']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['planning_period']),
        ]
        
    def __str__(self):
        return f"{self.template.name} - {self.date}"
    
    def is_in_past(self):
        """Check if shift is in the past"""
        return self.end_datetime < timezone.now()
    
    def can_be_modified(self):
        """Check if shift can still be modified"""
        return self.status.name in ['planned', 'published'] and not self.is_in_past()
    
    def get_assigned_count(self):
        """Get number of currently assigned engineers"""
        # Use direct query to avoid forward reference issues
        from django.apps import apps
        ShiftAssignment = apps.get_model('scheduling', 'ShiftAssignment')
        return ShiftAssignment.objects.filter(
            shift=self,
            status__name='active'
        ).count()
    
    def is_fully_staffed(self):
        """Check if shift has required number of engineers"""
        return self.get_assigned_count() >= self.template.engineers_required


class ShiftAssignment(models.Model):
    """
    Clean shift assignment model with proper status tracking
    """
    shift = models.ForeignKey(
        ShiftInstance,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shift_assignments'
    )
    
    # Assignment role
    ASSIGNMENT_ROLES = [
        ('primary', 'Primary Engineer'),
        ('backup', 'Backup Engineer'),
        ('trainee', 'Trainee'),
        ('observer', 'Observer'),
    ]
    
    assignment_role = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_ROLES,
        default='primary'
    )
    
    # Status using foundation model
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='shift_assignments'
    )
    
    # Assignment details
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_shifts'
    )
    
    # Acceptance tracking
    user_response = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Response'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined'),
            ('auto_accepted', 'Auto Accepted'),
        ],
        default='pending'
    )
    response_at = models.DateTimeField(null=True, blank=True)
    
    # Completion tracking
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Notes
    assignment_notes = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    
    # Audit fields
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_shift_assignments'
        unique_together = ['shift', 'user']
        indexes = [
            models.Index(fields=['shift']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['assignment_role']),
            models.Index(fields=['user_response']),
            models.Index(fields=['assigned_at']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.shift.template.name} ({self.shift.date})"
    
    def is_active(self):
        """Check if assignment is currently active"""
        return self.status.name == 'active'
    
    def calculate_hours_worked(self):
        """Calculate actual hours worked if times are recorded"""
        if self.actual_start_time and self.actual_end_time:
            duration = self.actual_end_time - self.actual_start_time
            return Decimal(str(duration.total_seconds() / 3600))
        return None


class PlanningPeriod(models.Model):
    """
    Clean planning period model with proper team relationships
    Planning periods for organizing and tracking shift assignments
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Period type
    PERIOD_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom Period'),
    ]
    
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
    
    # Status using foundation model
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='planning_periods'
    )
    
    # Priority for this planning period
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='planning_periods'
    )
    
    # Team relationships (missing from original)
    teams = models.ManyToManyField(
        Team,
        through='PlanningPeriodTeam',
        related_name='planning_periods'
    )
    
    # Configuration
    allows_auto_generation = models.BooleanField(
        default=True,
        help_text="Allow automatic shift generation for this period"
    )
    
    # Planning algorithm (extensible)
    planning_algorithm = models.ForeignKey(
        'PlanningAlgorithm',
        on_delete=models.PROTECT,
        related_name='planning_periods',
        null=True,
        blank=True
    )
    
    # Planning metadata
    planning_notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_planning_periods'
    )
    
    class Meta:
        db_table = 'tps_planning_periods'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['period_type']),
            models.Index(fields=['planning_deadline']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def is_in_planning_phase(self):
        """Check if period is currently in planning phase"""
        return self.status.name in ['draft', 'planning', 'review']
    
    def is_published(self):
        """Check if period has been published"""
        return self.status.name == 'published'
    
    def days_until_deadline(self):
        """Calculate days until planning deadline"""
        if self.planning_deadline:
            delta = self.planning_deadline.date() - timezone.now().date()
            return delta.days
        return None


class PlanningPeriodTeam(models.Model):
    """
    Team participation in planning periods (proper many-to-many)
    """
    planning_period = models.ForeignKey(
        PlanningPeriod,
        on_delete=models.CASCADE,
        related_name='period_teams'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='period_participations'
    )
    
    # Team-specific configuration for this period
    is_primary_team = models.BooleanField(
        default=True,
        help_text="Whether this team is primarily responsible for this period"
    )
    
    participation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage of team capacity allocated to this period"
    )
    
    # Priority for this team in this period
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='planning_period_teams'
    )
    
    # Notes specific to this team's participation
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_planning_period_teams'
        unique_together = ['planning_period', 'team']
        indexes = [
            models.Index(fields=['planning_period']),
            models.Index(fields=['team']),
            models.Index(fields=['is_primary_team']),
            models.Index(fields=['priority']),
        ]
        
    def __str__(self):
        return f"{self.planning_period.name} - {self.team.name}"


class PlanningAlgorithm(models.Model):
    """
    Extensible planning algorithms (replacing hard-coded choices)
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Algorithm configuration
    algorithm_class = models.CharField(
        max_length=200,
        help_text="Python class path for the algorithm implementation"
    )
    
    # Default parameters (structured configuration)
    default_parameters = models.JSONField(
        default=dict,
        help_text="Default algorithm parameters"
    )
    
    # Algorithm capabilities
    supports_auto_assignment = models.BooleanField(default=True)
    supports_fairness_optimization = models.BooleanField(default=True)
    supports_skill_matching = models.BooleanField(default=True)
    supports_preference_weighting = models.BooleanField(default=True)
    
    # Status and priority
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='planning_algorithms'
    )
    
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='planning_algorithms'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_planning_algorithms'
    )
    
    class Meta:
        db_table = 'tps_planning_algorithms'
        ordering = ['priority__order', 'name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
        
    def __str__(self):
        return self.display_name
