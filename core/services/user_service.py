"""
TPS V1.4 - User Service Layer
Centralized user management and operations
"""

from typing import Dict, Any, List, Optional
from django.db.models import QuerySet, Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from .base_service import BaseService
from apps.accounts.models import User, UserSkill
from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment


class UserService(BaseService):
    """
    Service for user-related business operations
    """
    
    def __init__(self, user: Optional[User] = None):
        super().__init__()
        self.user = user
    
    def get_user_profile_data(self, user: User = None) -> Dict[str, Any]:
        """
        Get comprehensive user profile data
        """
        target_user = user or self.user
        if not target_user:
            raise ValueError("User must be provided")
        
        return {
            'user': target_user,
            'ytd_stats': target_user.get_ytd_stats(),
            'skills': self.get_user_skills(target_user),
            'teams': self.get_user_teams(target_user),
            'role_permissions': self.get_role_permissions(target_user),
            'recent_assignments': self.get_recent_assignments(target_user),
        }
    
    def get_user_skills(self, user: User) -> QuerySet[UserSkill]:
        """
        Get user's skills with proficiency levels
        """
        return UserSkill.objects.filter(
            user=user
        ).select_related('skill__category').order_by('skill__category__name', 'skill__name')
    
    def get_user_teams(self, user: User) -> QuerySet[Team]:
        """
        Get teams the user belongs to or leads
        """
        return Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).distinct()
    
    def get_role_permissions(self, user: User) -> Dict[str, bool]:
        """
        Get user's role-based permissions
        """
        return {
            'can_access_planning': user.can_access_planning(),
            'can_access_analytics': user.can_access_analytics(),
            'can_manage_teams': user.can_manage_teams(),
            'is_team_leader': self.is_team_leader(user),
            'is_planner': user.is_planner(),
            'is_manager': user.is_manager(),
            'is_admin': user.is_admin(),
        }
    
    def get_recent_assignments(self, user: User, limit: int = 10) -> QuerySet[Assignment]:
        """
        Get user's recent assignments
        """
        return Assignment.objects.filter(
            user=user
        ).select_related(
            'shift__template', 'shift__template__category'
        ).order_by('-assigned_at')[:limit]
    
    def is_team_leader(self, user: User) -> bool:
        """
        Check if user is a team leader
        """
        return Team.objects.filter(team_leader=user).exists()
    
    def get_workload_stats(self, user: User, period_days: int = 30) -> Dict[str, Any]:
        """
        Get user's workload statistics for a given period
        """
        start_date = self.current_date - timedelta(days=period_days)
        
        assignments = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=start_date,
            status__in=['confirmed', 'completed']
        )
        
        total_assignments = assignments.count()
        total_hours = assignments.aggregate(
            total=Sum('shift__template__duration_hours')
        )['total'] or 0
        
        # Weekly breakdown
        weekly_assignments = assignments.filter(
            shift__start_datetime__gte=self.current_date - timedelta(days=7)
        ).count()
        
        return {
            'period_days': period_days,
            'total_assignments': total_assignments,
            'total_hours': float(total_hours),
            'weekly_assignments': weekly_assignments,
            'avg_assignments_per_week': round(total_assignments / (period_days / 7), 1),
            'avg_hours_per_week': round(float(total_hours) / (period_days / 7), 1),
        }
    
    def can_take_assignment(self, user: User, shift_template) -> Dict[str, Any]:
        """
        Check if user can take a specific assignment based on business rules
        """
        category = shift_template.category.name
        
        # Check basic availability
        if not user.is_active_employee:
            return {
                'can_assign': False,
                'reason': 'User is not an active employee'
            }
        
        # Check year-to-date limits
        if category == 'WAAKDIENST' and not user.can_work_waakdienst():
            return {
                'can_assign': False,
                'reason': f'User has reached annual waakdienst limit ({user.ytd_waakdienst_weeks}/8 weeks)'
            }
        
        if category == 'INCIDENT' and not user.can_work_incident():
            return {
                'can_assign': False,
                'reason': f'User has reached annual incident limit ({user.ytd_incident_weeks}/12 weeks)'
            }
        
        # Check required skills
        required_skills = shift_template.required_skills or []
        if required_skills:
            user_skills = set(
                UserSkill.objects.filter(
                    user=user,
                    skill__id__in=required_skills
                ).values_list('skill__id', flat=True)
            )
            
            missing_skills = set(required_skills) - user_skills
            if missing_skills:
                return {
                    'can_assign': False,
                    'reason': f'User lacks required skills: {missing_skills}'
                }
        
        return {
            'can_assign': True,
            'reason': 'User meets all requirements'
        }
    
    def get_availability_conflicts(self, user: User, start_datetime, end_datetime) -> List[Dict[str, Any]]:
        """
        Check for availability conflicts for a user in a given time period
        """
        conflicts = []
        
        # Check existing assignments
        existing_assignments = Assignment.objects.filter(
            user=user,
            shift__start_datetime__lt=end_datetime,
            shift__end_datetime__gt=start_datetime,
            status__in=['confirmed', 'pending_confirmation', 'in_progress']
        ).select_related('shift__template')
        
        for assignment in existing_assignments:
            conflicts.append({
                'type': 'assignment',
                'start': assignment.shift.start_datetime,
                'end': assignment.shift.end_datetime,
                'description': f"Assigned to {assignment.shift.template.name}",
                'severity': 'high'
            })
        
        # Check blackout dates (if implemented)
        blackout_dates = user.blackout_dates or []
        for blackout_period in blackout_dates:
            # Assuming blackout_dates format: [{"start": "2024-01-01", "end": "2024-01-07", "reason": "vacation"}]
            if self._date_ranges_overlap(
                blackout_period.get('start'),
                blackout_period.get('end'),
                start_datetime.date(),
                end_datetime.date()
            ):
                conflicts.append({
                    'type': 'blackout',
                    'start': blackout_period.get('start'),
                    'end': blackout_period.get('end'),
                    'description': blackout_period.get('reason', 'Unavailable'),
                    'severity': 'medium'
                })
        
        return conflicts
    
    def _date_ranges_overlap(self, start1, end1, start2, end2) -> bool:
        """
        Check if two date ranges overlap
        """
        try:
            # Convert strings to dates if needed
            if isinstance(start1, str):
                from datetime import datetime
                start1 = datetime.strptime(start1, '%Y-%m-%d').date()
            if isinstance(end1, str):
                from datetime import datetime
                end1 = datetime.strptime(end1, '%Y-%m-%d').date()
            
            return start1 <= end2 and end1 >= start2
        except (ValueError, AttributeError):
            return False
    
    def update_ytd_stats(self, user: User) -> Dict[str, Any]:
        """
        Recalculate and update user's year-to-date statistics
        """
        current_year = self.current_date.year
        year_start = self.current_date.replace(month=1, day=1)
        
        # Calculate waakdienst weeks
        waakdienst_assignments = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=year_start,
            shift__template__category__name='WAAKDIENST',
            status__in=['confirmed', 'completed']
        ).count()
        
        # Calculate incident weeks
        incident_assignments = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=year_start,
            shift__template__category__name='INCIDENT',
            status__in=['confirmed', 'completed']
        ).count()
        
        # Calculate total hours
        total_hours = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=year_start,
            status__in=['confirmed', 'completed']
        ).aggregate(
            total=Sum('shift__template__duration_hours')
        )['total'] or 0
        
        # Update user model
        user.ytd_waakdienst_weeks = waakdienst_assignments
        user.ytd_incident_weeks = incident_assignments  
        user.ytd_hours_logged = total_hours
        user.save(update_fields=['ytd_waakdienst_weeks', 'ytd_incident_weeks', 'ytd_hours_logged'])
        
        return user.get_ytd_stats()
    
    @staticmethod
    def get_active_users() -> QuerySet[User]:
        """
        Get all active users
        """
        return User.objects.filter(
            is_active=True,
            is_active_employee=True
        )
    
    @staticmethod
    def get_users_by_role(role: str) -> QuerySet[User]:
        """
        Get users by role
        """
        return User.objects.filter(role=role, is_active=True)
    
    @staticmethod
    def get_team_members(team: Team) -> QuerySet[User]:
        """
        Get active members of a team
        """
        return User.objects.filter(
            team_memberships__team=team,
            team_memberships__is_active=True,
            is_active_employee=True
        )