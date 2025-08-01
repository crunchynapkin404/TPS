"""
TPS V1.4 - Dashboard Service Layer
Implements strategy pattern for role-based dashboard contexts
"""

from typing import Dict, Any, List
from abc import abstractmethod
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from .base_service import ContextService, PermissionService
from apps.teams.models import Team
from apps.assignments.models import Assignment
from apps.accounts.models import User


class DashboardStrategy(ContextService):
    """
    Abstract strategy for dashboard context building
    """
    
    @abstractmethod
    def build_context(self) -> Dict[str, Any]:
        """Build role-specific dashboard context"""
        pass
    
    def get_common_stats(self) -> Dict[str, Any]:
        """Get statistics common across dashboard types"""
        return {
            'user_teams': PermissionService.get_user_teams(self.user),
            'is_team_leader': PermissionService.is_team_leader(self.user),
        }


class AdminDashboardStrategy(DashboardStrategy):
    """
    Strategy for admin dashboard - system overview
    """
    
    def build_context(self) -> Dict[str, Any]:
        context = self.get_base_context()
        context.update(self.get_common_stats())
        context.update({
            'dashboard_type': 'admin',
            **self._get_system_metrics_optimized(),
            'recent_activity': self._get_recent_activity(),
        })
        return context
    
    def _get_system_metrics_optimized(self) -> Dict[str, Any]:
        """Get system-wide metrics using optimized query service"""
        from core.services.query_optimization_service import QueryOptimizationService
        
        # Use the optimized query service for comprehensive metrics
        system_metrics = QueryOptimizationService.get_system_health_metrics()
        
        return {
            'total_users': system_metrics['total_active_users'],
            'total_teams': system_metrics['total_teams'],
            'total_assignments_this_week': system_metrics['total_assignments_week'],
            'system_health': system_metrics['success_rate'],
            'pending_leave_requests': system_metrics['pending_leave_requests'],
            'user_engagement_rate': system_metrics['user_engagement_rate'],
            'team_utilization_rate': system_metrics['team_utilization_rate'],
            'auto_assignment_rate': system_metrics['auto_assignment_rate'],
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics - OPTIMIZED with single query"""
        from django.db.models import Count, Case, When, IntegerField
        
        # Get all metrics in single aggregated query
        metrics = Assignment.objects.filter(
            shift__start_datetime__gte=self.week_start,
            shift__start_datetime__lte=self.week_end
        ).aggregate(
            total_assignments_this_week=Count('id'),
            # Count unique users and teams involved this week
            active_users_this_week=Count('user', distinct=True),
            teams_this_week=Count('shift__planning_period__teams', distinct=True)
        )
        
        # Get total counts separately but cache them
        total_counts = User.objects.aggregate(
            total_active_users=Count('id', filter=Q(is_active=True))
        )
        
        team_count = Team.objects.count()
        
        return {
            'total_users': total_counts['total_active_users'],
            'total_teams': team_count,
            'total_assignments_this_week': metrics['total_assignments_this_week'],
            'active_users_this_week': metrics['active_users_this_week'],
            'teams_with_assignments_this_week': metrics['teams_this_week'],
        }
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Calculate system health metrics - OPTIMIZED with single query"""
        from django.db.models import Count, Case, When, FloatField
        
        # Get assignment statistics in single query
        assignment_stats = Assignment.objects.filter(
            assigned_at__gte=self.current_date - timedelta(days=7)
        ).aggregate(
            total_assignments=Count('id'),
            failed_assignments=Count('id', filter=Q(
                status__in=['declined', 'no_show', 'cancelled']
            ))
        )
        
        total_assignments = assignment_stats['total_assignments']
        failed_assignments = assignment_stats['failed_assignments']
        
        health_percentage = 100.0 if total_assignments == 0 else (
            (total_assignments - failed_assignments) / total_assignments
        ) * 100
        
        # Get pending leave requests in same query scope
        try:
            from apps.leave_management.models import LeaveRequest
            pending_leave_requests = LeaveRequest.objects.filter(
                status__in=['submitted', 'pending_hr']
            ).count()
        except ImportError:
            pending_leave_requests = 0
        
        return {
            'system_health': round(health_percentage, 1),
            'pending_leave_requests': pending_leave_requests,
            'total_assignments_last_week': total_assignments,
            'failed_assignments_last_week': failed_assignments,
        }
    
    def _get_recent_activity(self) -> List[Assignment]:
        """Get recent system activity"""
        return Assignment.objects.select_related(
            'user', 'shift__template'
        ).order_by('-assigned_at')[:10]


class ManagerDashboardStrategy(DashboardStrategy):
    """
    Strategy for manager dashboard - team management focus
    """
    
    def build_context(self) -> Dict[str, Any]:
        context = self.get_base_context()
        context.update(self.get_common_stats())
        
        managed_teams = self._get_managed_teams()
        context.update({
            'dashboard_type': 'manager',
            'managed_teams': managed_teams,
            'total_managed_teams': managed_teams.count(),
            'pending_approvals': self._get_pending_approvals(managed_teams),
            'pending_leave_approvals': self._get_pending_leave_approvals(managed_teams),
            'team_stats': self._get_team_stats(managed_teams),
        })
        return context
    
    def _get_managed_teams(self):
        """Get teams managed by this user"""
        return Team.objects.filter(team_leader=self.user)
    
    def _get_pending_approvals(self, managed_teams) -> List[Assignment]:
        """Get pending assignment approvals"""
        return Assignment.objects.filter(
            shift__planning_period__teams__in=managed_teams,
            status='pending_confirmation'
        ).select_related('user', 'shift__template')[:10]
    
    def _get_pending_leave_approvals(self, managed_teams) -> List:
        """Get pending leave request approvals"""
        from apps.leave_management.models import LeaveRequest
        return LeaveRequest.objects.filter(
            status__in=['submitted', 'pending_manager'],
            user__team_memberships__team__in=managed_teams
        ).distinct().select_related('user', 'leave_type')[:10]
    
    def _get_team_stats(self, managed_teams) -> List[Dict[str, Any]]:
        """Get performance stats for managed teams - OPTIMIZED to avoid N+1 queries"""
        from django.db.models import Count
        
        # Get team member counts in single query with annotation
        team_member_counts = {
            team.id: team.member_count 
            for team in managed_teams.annotate(
                member_count=Count('memberships', filter=Q(
                    memberships__is_active=True,
                    memberships__user__is_active_employee=True
                ))
            )
        }
        
        # Get assignment counts in single query with annotation
        team_assignment_counts = dict(
            Assignment.objects.filter(
                shift__planning_period__teams__in=managed_teams,
                shift__start_datetime__gte=self.week_start,
                shift__start_datetime__lte=self.week_end
            ).values('shift__planning_period__teams').annotate(
                assignment_count=Count('id')
            ).values_list('shift__planning_period__teams', 'assignment_count')
        )
        
        # Combine results
        team_stats = []
        for team in managed_teams:
            team_stats.append({
                'team': team,
                'members': team_member_counts.get(team.id, 0),
                'this_week_assignments': team_assignment_counts.get(team.id, 0),
            })
        
        return team_stats


class PlannerDashboardStrategy(DashboardStrategy):
    """
    Strategy for planner dashboard - planning and scheduling focus
    """
    
    def build_context(self) -> Dict[str, Any]:
        context = self.get_base_context()
        context.update(self.get_common_stats())
        
        user_teams = context['user_teams']
        context.update({
            'dashboard_type': 'planner',
            'planning_periods': self._get_planning_periods(user_teams),
            'unassigned_shifts': self._get_unassigned_shifts(user_teams),
            'planning_advice': self._generate_planning_advice(user_teams),
            'recent_planning_activity': self._get_recent_planning_activity(user_teams),
        })
        return context
    
    def _get_planning_periods(self, user_teams):
        """Get planning periods needing attention"""
        from apps.scheduling.models import PlanningPeriod
        return PlanningPeriod.objects.filter(
            teams__in=user_teams,
            start_date__gte=self.current_date,
            status__in=['draft', 'planning', 'review', 'approved']
        ).distinct()[:5]
    
    def _get_unassigned_shifts(self, user_teams):
        """Get unassigned shifts"""
        from apps.scheduling.models import ShiftInstance
        return ShiftInstance.objects.filter(
            planning_period__teams__in=user_teams,
            assignments__isnull=True,
            start_datetime__gte=self.current_date
        ).select_related('template', 'planning_period')[:10]
    
    def _generate_planning_advice(self, user_teams) -> List[Dict[str, Any]]:
        """Generate intelligent planning advice - OPTIMIZED to avoid N+1 queries"""
        from django.db.models import Count
        from apps.scheduling.models import ShiftInstance
        
        advice = []
        
        # Get unassigned shift counts for all teams in single query
        team_unassigned_counts = dict(
            ShiftInstance.objects.filter(
                planning_period__teams__in=user_teams,
                start_datetime__gte=self.current_date,
                start_datetime__lte=self.current_date + timedelta(days=14),
                assignments__isnull=True
            ).values('planning_period__teams').annotate(
                unassigned_count=Count('id')
            ).values_list('planning_period__teams', 'unassigned_count')
        )
        
        # Check for understaffed periods using pre-calculated counts
        for team in user_teams[:3]:  # Limit for performance
            upcoming_shifts = team_unassigned_counts.get(team.id, 0)
            
            if upcoming_shifts > 5:
                advice.append({
                    'type': 'warning',
                    'title': f'Understaffed: {team.name}',
                    'message': f'{upcoming_shifts} unassigned shifts in the next 2 weeks',
                    'action': 'Review staffing levels'
                })
        
        # Default advice if no critical issues
        if not advice:
            advice.append({
                'type': 'info',
                'title': 'Workload Distribution',
                'message': 'Consider rotating weekend assignments for better work-life balance',
                'action': 'View fairness report'
            })
        
        return advice
    
    def _get_recent_planning_activity(self, user_teams) -> List[Assignment]:
        """Get recent planning activity"""
        return Assignment.objects.filter(
            shift__planning_period__teams__in=user_teams
        ).select_related('user', 'shift__template').order_by('-assigned_at')[:10]


class UserDashboardStrategy(DashboardStrategy):
    """
    Strategy for user dashboard - personal focus
    """
    
    def build_context(self) -> Dict[str, Any]:
        context = self.get_base_context()
        context.update(self.get_common_stats())
        context.update({
            'dashboard_type': 'user',
            **self._get_user_dashboard_data_optimized(),
            'personal_advice': self._generate_personal_advice(),
        })
        return context
    
    def _get_user_dashboard_data_optimized(self) -> Dict[str, Any]:
        """Get user dashboard data using optimized query service"""
        from core.services.query_optimization_service import QueryOptimizationService
        
        # Use optimized service for user dashboard data
        dashboard_data = QueryOptimizationService.get_user_dashboard_data(self.user)
        
        # Get leave requests separately (if leave management is available)
        try:
            leave_requests = self._get_leave_requests()
        except ImportError:
            leave_requests = []
        
        # Get today's assignments
        daily_assignments = self._get_daily_assignments()
        
        return {
            'upcoming_shifts': dashboard_data['upcoming_shifts'],
            'assignment_stats': dashboard_data['assignment_stats'],
            'my_leave_requests': leave_requests,
            **daily_assignments,
        }
    
    def _get_upcoming_shifts(self) -> List[Assignment]:
        """Get user's upcoming shifts"""
        return Assignment.objects.filter(
            user=self.user,
            shift__start_datetime__gt=self.current_time
        ).select_related('shift__template').order_by('shift__start_datetime')[:8]
    
    def _get_leave_requests(self) -> List:
        """Get user's leave requests"""
        from apps.leave_management.models import LeaveRequest
        return LeaveRequest.objects.filter(
            user=self.user
        ).select_related('leave_type').order_by('-created_at')[:5]
    
    def _get_daily_assignments(self) -> Dict[str, Any]:
        """Get today's engineer assignments"""
        incident_engineer = Assignment.objects.filter(
            shift__date=self.current_date,
            shift__template__category__name='INCIDENT',
            status__in=['confirmed', 'completed', 'in_progress']
        ).select_related('user', 'shift__template').first()
        
        waakdienst_engineer = Assignment.objects.filter(
            shift__date=self.current_date,
            shift__template__category__name='WAAKDIENST',
            status__in=['confirmed', 'completed', 'in_progress']
        ).select_related('user', 'shift__template').first()
        
        total_working = Assignment.objects.filter(
            shift__date=self.current_date,
            status__in=['confirmed', 'completed', 'in_progress']
        ).values('user').distinct().count()
        
        return {
            'incident_engineer_today': incident_engineer,
            'waakdienst_engineer_today': waakdienst_engineer,
            'total_working_today': total_working,
        }
    
    def _generate_personal_advice(self) -> List[Dict[str, Any]]:
        """Generate personal advice for users"""
        advice = []
        
        # Check upcoming workload
        next_week_shifts = Assignment.objects.filter(
            user=self.user,
            shift__start_datetime__gte=self.current_date + timedelta(days=7),
            shift__start_datetime__lte=self.current_date + timedelta(days=14)
        ).count()
        
        if next_week_shifts > 5:
            advice.append({
                'type': 'info',
                'title': 'Busy Week Ahead',
                'message': f'You have {next_week_shifts} shifts scheduled next week',
                'action': 'Consider planning rest time'
            })
        
        # Check leave balance
        try:
            from apps.leave_management.models import LeaveBalance
            annual_balance = LeaveBalance.objects.get(
                user=self.user,
                leave_type__code='ANNUAL',
                year=self.current_date.year
            )
            if annual_balance.remaining > 10:
                advice.append({
                    'type': 'success',
                    'title': 'Plan Your Vacation',
                    'message': f'You have {annual_balance.remaining:.1f} days of annual leave remaining',
                    'action': 'Book time off'
                })
        except:  # LeaveBalance.DoesNotExist or other issues
            pass
        
        return advice


class DashboardService:
    """
    Main dashboard service using strategy pattern
    """
    
    STRATEGIES = {
        'ADMIN': AdminDashboardStrategy,
        'MANAGER': ManagerDashboardStrategy,
        'PLANNER': PlannerDashboardStrategy,
        'USER': UserDashboardStrategy,
    }
    
    @classmethod
    def get_dashboard_context(cls, user: User) -> Dict[str, Any]:
        """
        Get dashboard context for the given user based on their role
        """
        strategy_class = cls.STRATEGIES.get(user.role, UserDashboardStrategy)
        strategy = strategy_class(user)
        return strategy.build_context()
    
    @classmethod
    def get_strategy_for_user(cls, user: User) -> DashboardStrategy:
        """
        Get the appropriate dashboard strategy for a user
        """
        strategy_class = cls.STRATEGIES.get(user.role, UserDashboardStrategy)
        return strategy_class(user)