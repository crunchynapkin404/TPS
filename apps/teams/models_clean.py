"""
TPS V1.4 - Clean Teams Models
Team management with proper Django relationships (no JSONField abuse)
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

from core.models import Status, Priority, Skill, SkillCategory, ShiftCategory


class Team(models.Model):
    """
    Clean Team model with proper relationships
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    
    # Team Leadership
    team_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams'
    )
    
    deputy_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deputy_led_teams'
    )
    
    # Status using foundation model
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='teams'
    )
    
    # Staffing Configuration
    min_members_per_shift = models.PositiveIntegerField(default=1)
    max_members_per_shift = models.PositiveIntegerField(default=5)
    preferred_team_size = models.PositiveIntegerField(default=8)
    
    # Contact Information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Configuration
    allows_auto_assignment = models.BooleanField(
        default=True,
        help_text="Allow automatic shift assignments for this team"
    )
    
    # Team specializations (many-to-many with shift categories)
    shift_categories = models.ManyToManyField(
        ShiftCategory,
        through='TeamShiftCategory',
        related_name='teams'
    )
    
    # Required skills for team membership
    required_skills = models.ManyToManyField(
        Skill,
        through='TeamSkillRequirement',
        related_name='required_by_teams'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_teams'
        ordering = ['name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['department']),
            models.Index(fields=['team_leader']),
        ]
        
    def __str__(self):
        return self.name
    
    def get_active_members(self):
        """Get all active team members"""
        # Use direct query to avoid forward reference issues
        from django.apps import apps
        TeamMembership = apps.get_model('teams', 'TeamMembership')
        return TeamMembership.objects.filter(
            team=self,
            status__name='active',
            user__is_active=True
        ).select_related('user', 'role', 'status')
    
    def get_member_count(self):
        """Get count of active members"""
        return self.get_active_members().count()
    
    def can_accommodate_shift(self, required_engineers=1):
        """Check if team has enough members for a shift"""
        active_count = self.get_member_count()
        return active_count >= required_engineers
    
    def has_required_skills_coverage(self):
        """Check if team has all required skills covered"""
        required_skills = self.required_skills.all()
        member_skills = Skill.objects.filter(
            user_skills__user__team_memberships__team=self,
            user_skills__user__team_memberships__status__name='active'
        ).distinct()
        
        return set(required_skills).issubset(set(member_skills))


class TeamRole(models.Model):
    """
    Extensible team roles (no hard-coded choices)
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Role hierarchy
    parent_role = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_roles'
    )
    
    # Permissions
    can_assign_shifts = models.BooleanField(default=False)
    can_approve_swaps = models.BooleanField(default=False)
    can_manage_team = models.BooleanField(default=False)
    can_approve_leave = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=False)
    
    # Role priority (for conflict resolution)
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_roles'
    )
    
    # Status
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='team_roles'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_roles'
        ordering = ['priority__order', 'name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
        
    def __str__(self):
        return self.display_name


class TeamMembership(models.Model):
    """
    Clean user-team relationship with proper status tracking
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.ForeignKey(
        TeamRole,
        on_delete=models.PROTECT,
        related_name='memberships'
    )
    
    # Status using foundation model
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='team_memberships'
    )
    
    # Membership Timeline
    join_date = models.DateField(default=timezone.now)
    leave_date = models.DateField(null=True, blank=True)
    
    # Membership Configuration
    is_primary_team = models.BooleanField(
        default=True,
        help_text="Whether this is the user's primary team assignment"
    )
    availability_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage of time available to this team"
    )
    
    # Assignment Priority
    assignment_priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_memberships',
        help_text="Priority for shift assignments within this team"
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_memberships'
        unique_together = ['user', 'team']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['team']),
            models.Index(fields=['status']),
            models.Index(fields=['role']),
            models.Index(fields=['is_primary_team']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.team.name} ({self.role.name})"
    
    def can_assign_shifts(self):
        """Check if member can assign shifts"""
        return self.role.can_assign_shifts
    
    def can_approve_swaps(self):
        """Check if member can approve swap requests"""
        return self.role.can_approve_swaps
    
    def is_active_member(self):
        """Check if membership is currently active"""
        return self.status.name == 'active' and self.user.is_active


class TeamShiftCategory(models.Model):
    """
    Team specializations in specific shift categories
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='team_shift_categories'
    )
    shift_category = models.ForeignKey(
        ShiftCategory,
        on_delete=models.CASCADE,
        related_name='team_specializations'
    )
    
    # Specialization level
    SPECIALIZATION_LEVELS = [
        ('primary', 'Primary Specialization'),
        ('secondary', 'Secondary Specialization'),
        ('capable', 'Capable'),
        ('training', 'In Training'),
    ]
    
    specialization_level = models.CharField(
        max_length=20,
        choices=SPECIALIZATION_LEVELS,
        default='capable'
    )
    
    # Priority for this shift category
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_shift_categories'
    )
    
    # Minimum team members required for this category
    min_members_required = models.PositiveIntegerField(default=1)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_shift_categories'
        unique_together = ['team', 'shift_category']
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['shift_category']),
            models.Index(fields=['specialization_level']),
            models.Index(fields=['priority']),
        ]
        
    def __str__(self):
        return f"{self.team.name} - {self.shift_category.name} ({self.specialization_level})"


class TeamSkillRequirement(models.Model):
    """
    Skills required for team membership (replacing JSONField)
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='team_skill_requirements'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='team_requirements'
    )
    
    # Requirement type
    REQUIREMENT_TYPES = [
        ('mandatory', 'Mandatory'),
        ('preferred', 'Preferred'),
        ('optional', 'Optional'),
        ('training_provided', 'Training Provided'),
    ]
    
    requirement_type = models.CharField(
        max_length=20,
        choices=REQUIREMENT_TYPES,
        default='preferred'
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
        default='beginner'
    )
    
    # Priority for this requirement
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_skill_requirements'
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_skill_requirements'
        unique_together = ['team', 'skill']
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['skill']),
            models.Index(fields=['requirement_type']),
            models.Index(fields=['minimum_proficiency']),
            models.Index(fields=['priority']),
        ]
        
    def __str__(self):
        return f"{self.team.name} - {self.skill.name} ({self.requirement_type})"


class TeamNotificationPreference(models.Model):
    """
    Team notification preferences (replacing JSONField notification_preferences)
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Notification types
    NOTIFICATION_TYPES = [
        ('shift_assigned', 'Shift Assigned'),
        ('shift_cancelled', 'Shift Cancelled'),
        ('schedule_published', 'Schedule Published'),
        ('swap_request', 'Swap Request'),
        ('swap_approved', 'Swap Approved'),
        ('leave_request', 'Leave Request'),
        ('team_announcement', 'Team Announcement'),
        ('system_alert', 'System Alert'),
    ]
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    
    # Delivery methods
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    
    # Notification timing
    advance_notice_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours of advance notice required"
    )
    
    # Recipients
    notify_team_leader = models.BooleanField(default=True)
    notify_all_members = models.BooleanField(default=False)
    notify_affected_only = models.BooleanField(default=True)
    
    # Priority level
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_notification_preferences'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_notification_preferences'
        unique_together = ['team', 'notification_type']
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_active']),
        ]
        
    def __str__(self):
        return f"{self.team.name} - {self.notification_type}"


class TeamSchedulePattern(models.Model):
    """
    Clean schedule patterns (replacing JSONField pattern_data)
    Reusable schedule templates for teams
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='schedule_patterns'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Pattern type
    PATTERN_TYPES = [
        ('weekly', 'Weekly Pattern'),
        ('monthly', 'Monthly Pattern'),
        ('quarterly', 'Quarterly Pattern'),
        ('custom', 'Custom Pattern'),
    ]
    
    pattern_type = models.CharField(max_length=20, choices=PATTERN_TYPES)
    
    # Pattern configuration (broken down from JSON)
    days_in_cycle = models.PositiveIntegerField(default=7)
    shifts_per_day = models.PositiveIntegerField(default=1)
    
    # Effective dates
    effective_start_date = models.DateField()
    effective_end_date = models.DateField(null=True, blank=True)
    
    # Status and priority
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='team_schedule_patterns'
    )
    
    priority = models.ForeignKey(
        Priority,
        on_delete=models.PROTECT,
        related_name='team_schedule_patterns'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_schedule_patterns'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_schedule_patterns'
        unique_together = ['team', 'name']
        indexes = [
            models.Index(fields=['team']),
            models.Index(fields=['pattern_type']),
            models.Index(fields=['status']),
            models.Index(fields=['effective_start_date', 'effective_end_date']),
        ]
        
    def __str__(self):
        return f"{self.team.name} - {self.name}"
    
    def is_currently_effective(self):
        """Check if pattern is currently in effect"""
        today = timezone.now().date()
        if self.effective_start_date > today:
            return False
        if self.effective_end_date and self.effective_end_date < today:
            return False
        return self.status.name == 'active'


class TeamSchedulePatternDay(models.Model):
    """
    Individual days within a schedule pattern (replacing JSON structure)
    """
    pattern = models.ForeignKey(
        TeamSchedulePattern,
        on_delete=models.CASCADE,
        related_name='pattern_days'
    )
    
    # Day configuration
    day_number = models.PositiveIntegerField(help_text="Day number in the cycle (1-based)")
    day_name = models.CharField(max_length=20, blank=True, help_text="Optional day name")
    
    # Staffing requirements
    required_members = models.PositiveIntegerField(default=1)
    preferred_members = models.PositiveIntegerField(default=1)
    
    # Shift times
    shift_start_time = models.TimeField()
    shift_end_time = models.TimeField()
    
    # Required skills for this day
    required_skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name='required_by_pattern_days'
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_schedule_pattern_days'
        unique_together = ['pattern', 'day_number']
        indexes = [
            models.Index(fields=['pattern']),
            models.Index(fields=['day_number']),
            models.Index(fields=['shift_start_time', 'shift_end_time']),
        ]
        
    def __str__(self):
        return f"{self.pattern.name} - Day {self.day_number}"
    
    def get_shift_duration_hours(self):
        """Calculate shift duration in hours"""
        from datetime import datetime, timedelta, time
        from django.utils.safestring import SafeString
        
        # Ensure we have proper time objects (not SafeString or string)
        start_time = self.shift_start_time
        end_time = self.shift_end_time
        
        # Handle SafeString or string inputs
        if isinstance(start_time, (str, SafeString)):
            from django.utils.dateparse import parse_time
            start_time = parse_time(str(start_time))
            
        if isinstance(end_time, (str, SafeString)):
            from django.utils.dateparse import parse_time
            end_time = parse_time(str(end_time))
        
        # Validate that we have proper time objects
        if not isinstance(start_time, time) or not isinstance(end_time, time):
            return 8.0  # Default 8-hour shift if parsing fails
        
        try:
            start = datetime.combine(datetime.today(), start_time)
            end = datetime.combine(datetime.today(), end_time)
            
            # Handle overnight shifts
            if end < start:
                end += timedelta(days=1)
                
            duration = end - start
            return duration.total_seconds() / 3600
        except (TypeError, ValueError) as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating shift duration: {e}. Start: {start_time}, End: {end_time}")
            return 8.0  # Default fallback
