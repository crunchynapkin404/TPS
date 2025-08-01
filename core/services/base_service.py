"""
TPS V1.4 - Base Service Layer
Abstract base classes for service implementation with common patterns
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, date, timedelta

User = get_user_model()


class BaseService(ABC):
    """
    Abstract base service class providing common functionality
    for all business logic services
    """
    
    def __init__(self):
        self.current_time = timezone.now()
        self.current_date = self.current_time.date()
    
    def get_current_week_range(self) -> tuple[date, date]:
        """Get the start and end dates of the current week (Monday-Sunday)"""
        start = self.current_date - timedelta(days=self.current_date.weekday())
        end = start + timedelta(days=6)
        return start, end
    
    def get_current_month_start(self) -> date:
        """Get the first day of the current month"""
        return self.current_date.replace(day=1)
    
    def get_date_range_filter(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate a date range filter for queryset filtering"""
        return {
            'date__gte': start_date,
            'date__lte': end_date
        }


class ContextService(BaseService):
    """
    Base service for building view contexts with common data
    """
    
    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.week_start, self.week_end = self.get_current_week_range()
        self.month_start = self.get_current_month_start()
    
    def get_base_context(self) -> Dict[str, Any]:
        """Get basic context data common to all views"""
        return {
            'current_user': self.user,
            'today': self.current_date,
            'current_time': self.current_time,
            'week_start': self.week_start,
            'week_end': self.week_end,
            'month_start': self.month_start,
        }
    
    @abstractmethod
    def build_context(self) -> Dict[str, Any]:
        """Build the complete context for the view"""
        pass


class PermissionService(BaseService):
    """
    Service for handling user permissions and role-based access
    """
    
    @staticmethod
    def can_access_planning(user: User) -> bool:
        """Check if user can access planning tools"""
        return user.role in ['PLANNER', 'MANAGER', 'ADMIN']
    
    @staticmethod
    def can_access_analytics(user: User) -> bool:
        """Check if user can access analytics dashboard"""
        return user.role in ['MANAGER', 'ADMIN']
    
    @staticmethod
    def can_manage_teams(user: User) -> bool:
        """Check if user can manage teams and users"""
        return user.role in ['MANAGER', 'ADMIN']
    
    @staticmethod
    def is_team_leader(user: User) -> bool:
        """Check if user is a team leader"""
        from apps.teams.models import Team
        return Team.objects.filter(team_leader=user).exists()
    
    @staticmethod
    def get_user_teams(user: User, include_led_teams: bool = True):
        """Get teams the user belongs to or leads"""
        from django.db.models import Q
        from apps.teams.models import Team
        
        query = Q(memberships__user=user)
        if include_led_teams:
            query |= Q(team_leader=user)
        
        return Team.objects.filter(query).distinct()