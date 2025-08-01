"""
TPS V1.4 - Team Models
Team organization, membership, and schedule templates
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Team(models.Model):
    """
    Enhanced Team model with configuration and staffing requirements
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
    
    # Staffing Configuration
    min_members_per_shift = models.PositiveIntegerField(default=1)
    max_members_per_shift = models.PositiveIntegerField(default=5)
    preferred_team_size = models.PositiveIntegerField(default=8)
    
    # Contact Information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    allows_auto_assignment = models.BooleanField(
        default=True,
        help_text="Allow automatic shift assignments for this team"
    )
    notification_preferences = models.JSONField(
        default=dict,
        help_text="Team-specific notification settings"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_teams'
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_active_members(self):
        """Get all active team members - CACHED for performance"""
        from core.services.cache_service import CacheService
        
        cache_key = f"team_active_members_{self.id}"
        cached_members = CacheService.get_user_teams(self.id)  # Reuse cache mechanism
        
        if cached_members is not None:
            return cached_members
        
        # Query with optimization
        active_members = self.memberships.filter(
            is_active=True,
            user__is_active_employee=True
        ).select_related('user').prefetch_related('user__user_skills__skill')
        
        # Cache the result (convert to list to avoid lazy evaluation issues)
        members_list = list(active_members)
        CacheService.set_user_teams(self.id, members_list)
        
        return active_members
    
    def get_member_count(self):
        """Get count of active members - OPTIMIZED"""
        # Use Django's efficient count() rather than len() on cached queryset
        return self.memberships.filter(
            is_active=True,
            user__is_active_employee=True
        ).count()
    
    def can_accommodate_shift(self, required_engineers=1):
        """Check if team has enough members for a shift"""
        active_count = self.get_member_count()
        return active_count >= required_engineers


class TeamRole(models.Model):
    """
    Roles that team members can have within a team
    """
    ROLE_CHOICES = [
        ('member', 'Team Member'),
        ('coordinator', 'Team Coordinator'),
        ('lead', 'Team Lead'),
        ('deputy_lead', 'Deputy Team Lead'),
        ('trainer', 'Team Trainer'),
        ('scheduler', 'Team Scheduler'),
        ('operationeel', 'Operationeel'),
        ('tactisch', 'Tactisch'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    can_assign_shifts = models.BooleanField(default=False)
    can_approve_swaps = models.BooleanField(default=False)
    can_manage_team = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'tps_team_roles'
        ordering = ['name']
        
    def __str__(self):
        return self.get_name_display()


class TeamMembership(models.Model):
    """
    Through model for User-Team relationship with roles and status
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
        on_delete=models.SET_DEFAULT,
        default=1,  # Assumes 'member' role has id=1
        related_name='memberships'
    )
    
    # Membership Status
    is_active = models.BooleanField(default=True)
    join_date = models.DateField(default=timezone.now)
    leave_date = models.DateField(null=True, blank=True)
    
    # Membership Configuration
    is_primary_team = models.BooleanField(
        default=True,
        help_text="Whether this is the user's primary team assignment"
    )
    availability_percentage = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Percentage of time available to this team"
    )
    
    # Preferences
    prefers_waakdienst = models.BooleanField(default=True)
    prefers_incident = models.BooleanField(default=True)
    weekend_availability = models.BooleanField(default=True)
    night_shift_availability = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_memberships'
        unique_together = ['user', 'team']
        verbose_name = 'Team Membership'
        verbose_name_plural = 'Team Memberships'
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.team.name} ({self.role.name})"
    
    def can_assign_shifts(self):
        """Check if member can assign shifts"""
        return self.role.can_assign_shifts
    
    def can_approve_swaps(self):
        """Check if member can approve swap requests"""
        return self.role.can_approve_swaps


class TeamScheduleTemplate(models.Model):
    """
    Reusable schedule templates for teams
    """
    TEMPLATE_TYPES = [
        ('weekly', 'Weekly Pattern'),
        ('monthly', 'Monthly Pattern'),
        ('quarterly', 'Quarterly Pattern'),
        ('custom', 'Custom Pattern'),
    ]
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='schedule_templates'
    )
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    
    # Template Configuration
    pattern_data = models.JSONField(
        help_text="JSON structure defining the schedule pattern"
    )
    effective_start_date = models.DateField()
    effective_end_date = models.DateField(null=True, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_team_schedule_templates'
        unique_together = ['team', 'name']
        ordering = ['team__name', 'name']
        
    def __str__(self):
        return f"{self.team.name} - {self.name}"
