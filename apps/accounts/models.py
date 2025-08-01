"""
TPS V1.4 - Enhanced User Model and Skills System
Based on V1.3.1 analysis in /home/bart/Planner/V1.4/docs/02-database-models-analysis.md
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class User(AbstractUser):
    """
    Enhanced User model extending Django's AbstractUser
    Centralized user management with skills and year tracking
    """
    # Employee Information
    employee_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Unique employee identifier"
    )
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    
    # Year-to-Date Tracking
    ytd_waakdienst_weeks = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(52)],
        help_text="Waakdienst weeks completed this year"
    )
    ytd_incident_weeks = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(52)],
        help_text="Incident weeks completed this year"
    )
    ytd_hours_logged = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total hours logged this year"
    )
    
    # Availability Preferences
    preferred_shift_types = models.JSONField(
        default=list,
        help_text="Array of preferred shift type categories"
    )
    blackout_dates = models.JSONField(
        default=list,
        help_text="Array of date ranges when unavailable"
    )
    max_consecutive_days = models.PositiveIntegerField(
        default=7,
        help_text="Maximum consecutive days willing to work"
    )
    
    # Role-based Access Control
    ROLE_CHOICES = [
        ('USER', 'User'),
        ('PLANNER', 'Planner'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Administrator'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='USER',
        help_text="User's role in the TPS system"
    )
    
    @property
    def is_user(self):
        return self.role == 'USER'
    
    def has_role(self, role):
        """Check if user has specific role or higher"""
        role_hierarchy = ['USER', 'PLANNER', 'MANAGER', 'ADMIN']
        user_level = role_hierarchy.index(self.role)
        required_level = role_hierarchy.index(role)
        return user_level >= required_level
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active_employee = models.BooleanField(
        default=True,
        help_text="Employee is active (different from user.is_active)"
    )
    
    class Meta:
        db_table = 'tps_users'
        verbose_name = 'TPS User'
        verbose_name_plural = 'TPS Users'
        
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    # Role-based helper methods
    def is_user(self):
        """Check if user has basic user role"""
        return self.role == 'USER'
    
    def is_planner(self):
        """Check if user can access planning features - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'is_planner' in cached_permissions:
                return cached_permissions['is_planner']
            
            # Calculate and cache
            result = self.role in ['PLANNER', 'MANAGER', 'ADMIN']
            permissions = {
                'role': self.role,
                'is_planner': result,
                'is_manager': self.role in ['MANAGER', 'ADMIN'],
                'is_admin': self.role == 'ADMIN',
                'can_access_planning': result,
                'can_access_analytics': self.role in ['MANAGER', 'ADMIN'],
                'can_manage_teams': self.role in ['MANAGER', 'ADMIN'],
            }
            CacheService.set_user_permissions(self.id, permissions)
            return result
        except ImportError:
            # Fallback if cache service not available
            return self.role in ['PLANNER', 'MANAGER', 'ADMIN']
    
    def is_manager(self):
        """Check if user has manager privileges - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'is_manager' in cached_permissions:
                return cached_permissions['is_manager']
            
            # Fallback to is_planner which will cache all permissions
            self.is_planner()  # This will cache all permissions
            return self.role in ['MANAGER', 'ADMIN']
        except ImportError:
            return self.role in ['MANAGER', 'ADMIN']
    
    def is_admin(self):
        """Check if user has admin privileges - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'is_admin' in cached_permissions:
                return cached_permissions['is_admin']
            
            # Fallback to is_planner which will cache all permissions
            self.is_planner()  # This will cache all permissions
            return self.role == 'ADMIN'
        except ImportError:
            return self.role == 'ADMIN'
    
    def can_access_planning(self):
        """Check if user can access planning tools - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'can_access_planning' in cached_permissions:
                return cached_permissions['can_access_planning']
            
            # Fallback to is_planner which will cache all permissions
            return self.is_planner()
        except ImportError:
            return self.is_planner()
    
    def can_access_analytics(self):
        """Check if user can access analytics dashboard - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'can_access_analytics' in cached_permissions:
                return cached_permissions['can_access_analytics']
            
            # Fallback to is_planner which will cache all permissions
            self.is_planner()  # This will cache all permissions
            return self.role in ['MANAGER', 'ADMIN']
        except ImportError:
            return self.role in ['MANAGER', 'ADMIN']
    
    def can_manage_teams(self):
        """Check if user can manage teams and users - CACHED"""
        try:
            from core.services.cache_service import CacheService
            
            cached_permissions = CacheService.get_user_permissions(self.id)
            if cached_permissions and 'can_manage_teams' in cached_permissions:
                return cached_permissions['can_manage_teams']
            
            # Fallback to is_planner which will cache all permissions
            self.is_planner()  # This will cache all permissions
            return self.role in ['MANAGER', 'ADMIN']
        except ImportError:
            return self.role in ['MANAGER', 'ADMIN']
    
    def get_ytd_stats(self):
        """Get year-to-date statistics summary"""
        return {
            'waakdienst_weeks': self.ytd_waakdienst_weeks,
            'incident_weeks': self.ytd_incident_weeks,
            'total_hours': float(self.ytd_hours_logged),
            'remaining_waakdienst': 8 - self.ytd_waakdienst_weeks,
            'remaining_incident': 12 - self.ytd_incident_weeks,
        }
    
    def can_work_waakdienst(self):
        """Check if user can take waakdienst shifts"""
        return self.ytd_waakdienst_weeks < 8
    
    def can_work_incident(self):
        """Check if user can take incident shifts"""
        return self.ytd_incident_weeks < 12


class SkillCategory(models.Model):
    """
    Categories for organizing skills (e.g., Network, Security, Development)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7, 
        default='#6B7280',
        help_text="Hex color code for UI display"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tps_skill_categories'
        verbose_name = 'Skill Category'
        verbose_name_plural = 'Skill Categories'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Skill(models.Model):
    """
    Individual skills that engineers can possess
    """
    SKILL_LEVELS = [
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.CASCADE,
        related_name='skills'
    )
    description = models.TextField(blank=True)
    minimum_level_required = models.CharField(
        max_length=12,
        choices=SKILL_LEVELS,
        default='basic',
        help_text="Minimum skill level required for assignments"
    )
    requires_certification = models.BooleanField(
        default=False,
        help_text="Whether this skill requires active certification"
    )
    certification_validity_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How long certifications are valid (months)"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tps_skills'
        ordering = ['category__name', 'name']
        
    def __str__(self):
        return f"{self.category.name}: {self.name}"


class UserSkill(models.Model):
    """
    Through model for User-Skill relationship with proficiency tracking
    """
    PROFICIENCY_LEVELS = [
        ('learning', 'Learning'),
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_skills'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='user_skills'
    )
    proficiency_level = models.CharField(
        max_length=12,
        choices=PROFICIENCY_LEVELS,
        default='basic'
    )
    
    # Certification Tracking
    is_certified = models.BooleanField(default=False)
    certification_date = models.DateField(null=True, blank=True)
    certification_expiry = models.DateField(null=True, blank=True)
    certification_authority = models.CharField(max_length=100, blank=True)
    
    # Metadata
    acquired_date = models.DateField(default=timezone.now)
    last_used_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_user_skills'
        unique_together = ['user', 'skill']
        verbose_name = 'User Skill'
        verbose_name_plural = 'User Skills'
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.skill.name} ({self.proficiency_level})"
    
    def is_certification_valid(self):
        """Check if certification is still valid"""
        if not self.is_certified or not self.certification_expiry:
            return False
        return self.certification_expiry >= timezone.now().date()
    
    def meets_minimum_requirement(self):
        """Check if user's proficiency meets skill's minimum requirement"""
        proficiency_order = ['learning', 'basic', 'intermediate', 'advanced', 'expert']
        user_level_index = proficiency_order.index(self.proficiency_level)
        required_level_index = proficiency_order.index(self.skill.minimum_level_required)
        return user_level_index >= required_level_index


# Add skills to User model through related manager
User.add_to_class('skills', models.ManyToManyField(
    Skill,
    through=UserSkill,
    related_name='users',
    blank=True
))
