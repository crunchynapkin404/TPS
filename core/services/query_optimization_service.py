"""
TPS V1.4 - Query Optimization Service
Centralized service for complex database queries with performance optimizations
"""

from typing import Dict, List, Any, Optional, Union
from django.db.models import Q, Count, Sum, Avg, F, Case, When, Value, IntegerField
from django.db.models.query import QuerySet
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment
from core.services.cache_service import CacheService

User = get_user_model()


class QueryOptimizationService:
    """
    Service for optimizing complex database queries
    Implements patterns to reduce N+1 queries and optimize data retrieval
    """
    
    @classmethod
    def get_user_dashboard_data(cls, user: User) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a user in minimal queries
        Replaces multiple separate queries with optimized combined queries
        """
        cache_key = f"user_dashboard_{user.id}"
        cached_data = CacheService.get_dashboard_data(user.id, user.role)
        
        if cached_data:
            return cached_data
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Single query for user's assignments with all needed relationships
        user_assignments = Assignment.objects.filter(
            user=user
        ).select_related(
            'shift__template',
            'shift__planning_period',
            'assigned_by'
        ).prefetch_related(
            'shift__planning_period__teams'
        )
        
        # Aggregate assignment statistics
        assignment_stats = user_assignments.aggregate(
            total_assignments=Count('id'),
            this_week_assignments=Count(
                'id', 
                filter=Q(
                    shift__start_datetime__gte=week_start,
                    shift__start_datetime__lte=week_end
                )
            ),
            upcoming_assignments=Count(
                'id',
                filter=Q(
                    shift__start_datetime__gt=today,
                    status__in=['confirmed', 'pending_confirmation']
                )
            ),
            completed_assignments=Count(
                'id',
                filter=Q(status='completed')
            ),
            pending_confirmations=Count(
                'id',
                filter=Q(status='pending_confirmation')
            )
        )
        
        # Get upcoming shifts (next 7 days)
        upcoming_shifts = user_assignments.filter(
            shift__start_datetime__gt=timezone.now(),
            shift__start_datetime__lte=timezone.now() + timedelta(days=7),
            status__in=['confirmed', 'pending_confirmation']
        ).order_by('shift__start_datetime')[:5]
        
        dashboard_data = {
            'assignment_stats': assignment_stats,
            'upcoming_shifts': list(upcoming_shifts),
            'user_teams': cls.get_user_teams_optimized(user.id),
            'generated_at': timezone.now(),
        }
        
        # Cache the result
        CacheService.set_dashboard_data(user.id, user.role, dashboard_data)
        
        return dashboard_data
    
    @classmethod
    def get_user_teams_optimized(cls, user_id: int) -> List[Team]:
        """
        Get user's teams with optimized query and caching
        """
        cached_teams = CacheService.get_user_teams(user_id)
        if cached_teams is not None:
            return cached_teams
        
        # Optimized query with select_related and prefetch_related
        teams = list(
            Team.objects.filter(
                memberships__user_id=user_id,
                memberships__is_active=True,
                is_active=True
            ).select_related(
                'team_leader'
            ).prefetch_related(
                'memberships__user',
                'memberships__role'
            ).distinct()
        )
        
        # Cache the result
        CacheService.set_user_teams(user_id, teams)
        
        return teams
    
    @classmethod
    def get_team_workload_stats(cls, team_ids: List[int], 
                               date_range: tuple = None) -> Dict[int, Dict[str, Any]]:
        """
        Get workload statistics for multiple teams in single query
        Replaces N+1 queries with efficient bulk operations
        """
        if not date_range:
            today = timezone.now().date()
            date_range = (
                today - timedelta(days=30),
                today + timedelta(days=30)
            )
        
        start_date, end_date = date_range
        
        # Get assignment statistics for all teams in single query
        team_stats = Assignment.objects.filter(
            shift__planning_period__teams__id__in=team_ids,
            shift__start_datetime__gte=start_date,
            shift__start_datetime__lte=end_date
        ).values(
            'shift__planning_period__teams__id'
        ).annotate(
            total_assignments=Count('id'),
            confirmed_assignments=Count('id', filter=Q(status='confirmed')),
            pending_assignments=Count('id', filter=Q(status='pending_confirmation')),
            completed_assignments=Count('id', filter=Q(status='completed')),
            cancelled_assignments=Count('id', filter=Q(status__in=['cancelled', 'declined', 'no_show'])),
            unique_users=Count('user', distinct=True)
        )
        
        # Convert to dictionary for easy lookup
        stats_dict = {
            stat['shift__planning_period__teams__id']: {
                'total_assignments': stat['total_assignments'],
                'confirmed_assignments': stat['confirmed_assignments'],
                'pending_assignments': stat['pending_assignments'],
                'completed_assignments': stat['completed_assignments'],
                'cancelled_assignments': stat['cancelled_assignments'],
                'unique_users': stat['unique_users'],
                'success_rate': (
                    (stat['completed_assignments'] / stat['total_assignments'] * 100)
                    if stat['total_assignments'] > 0 else 0
                )
            }
            for stat in team_stats
        }
        
        # Fill in missing teams with zero stats
        for team_id in team_ids:
            if team_id not in stats_dict:
                stats_dict[team_id] = {
                    'total_assignments': 0,
                    'confirmed_assignments': 0,
                    'pending_assignments': 0,
                    'completed_assignments': 0,
                    'cancelled_assignments': 0,
                    'unique_users': 0,
                    'success_rate': 0.0
                }
        
        return stats_dict
    
    @classmethod
    def get_system_health_metrics(cls) -> Dict[str, Any]:
        """
        Get system-wide health metrics in optimized queries
        """
        cached_metrics = CacheService.get_system_stats()
        if cached_metrics:
            return cached_metrics
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Get comprehensive assignment statistics
        assignment_metrics = Assignment.objects.filter(
            assigned_at__gte=week_ago
        ).aggregate(
            total_assignments=Count('id'),
            successful_assignments=Count('id', filter=Q(status='completed')),
            failed_assignments=Count('id', filter=Q(
                status__in=['cancelled', 'declined', 'no_show']
            )),
            pending_assignments=Count('id', filter=Q(
                status='pending_confirmation'
            )),
            auto_assigned=Count('id', filter=Q(auto_assigned=True)),
            forced_assigned=Count('id', filter=Q(force_assigned=True))
        )
        
        # Calculate health percentages
        total = assignment_metrics['total_assignments']
        success_rate = (
            (assignment_metrics['successful_assignments'] / total * 100)
            if total > 0 else 100.0
        )
        
        # Get user and team counts
        user_team_stats = User.objects.aggregate(
            total_active_users=Count('id', filter=Q(
                is_active=True, 
                is_active_employee=True
            )),
            users_with_assignments=Count('id', filter=Q(
                shift_assignments__assigned_at__gte=week_ago
            ), distinct=True)
        )
        
        team_stats = Team.objects.aggregate(
            total_teams=Count('id', filter=Q(is_active=True)),
            teams_with_assignments=Count('id', filter=Q(
                planning_periods__shifts__assignments__assigned_at__gte=week_ago
            ), distinct=True)
        )
        
        # Get leave request statistics
        try:
            from apps.leave_management.models import LeaveRequest
            leave_stats = LeaveRequest.objects.aggregate(
                pending_leave_requests=Count('id', filter=Q(
                    status__in=['submitted', 'pending_manager', 'pending_hr']
                ))
            )
        except ImportError:
            leave_stats = {'pending_leave_requests': 0}
        
        metrics = {
            'success_rate': round(success_rate, 1),
            'total_assignments_week': total,
            'failed_assignments_week': assignment_metrics['failed_assignments'],
            'pending_assignments': assignment_metrics['pending_assignments'],
            'auto_assignment_rate': (
                (assignment_metrics['auto_assigned'] / total * 100)
                if total > 0 else 0.0
            ),
            'forced_assignment_rate': (
                (assignment_metrics['forced_assigned'] / total * 100)
                if total > 0 else 0.0
            ),
            'user_engagement_rate': (
                (user_team_stats['users_with_assignments'] / 
                 user_team_stats['total_active_users'] * 100)
                if user_team_stats['total_active_users'] > 0 else 0.0
            ),
            'team_utilization_rate': (
                (team_stats['teams_with_assignments'] / team_stats['total_teams'] * 100)
                if team_stats['total_teams'] > 0 else 0.0
            ),
            **user_team_stats,
            **team_stats,
            **leave_stats,
            'calculated_at': timezone.now()
        }
        
        # Cache the metrics
        CacheService.set_system_stats(metrics)
        
        return metrics
    
    @classmethod
    def get_user_workload_analysis(cls, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive workload analysis for a user
        """
        user = User.objects.get(id=user_id)
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        end_date = today + timedelta(days=days)
        
        # Single query for all user assignments in date range
        assignments = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=start_date,
            shift__start_datetime__lte=end_date
        ).select_related(
            'shift__template',
            'shift__planning_period'
        ).prefetch_related(
            'shift__planning_period__teams'
        )
        
        # Analyze workload patterns
        workload_stats = assignments.aggregate(
            total_assignments=Count('id'),
            past_assignments=Count('id', filter=Q(
                shift__start_datetime__lt=timezone.now()
            )),
            future_assignments=Count('id', filter=Q(
                shift__start_datetime__gte=timezone.now()
            )),
            weekend_assignments=Count('id', filter=Q(
                shift__start_datetime__week_day__in=[1, 7]  # Sunday=1, Saturday=7
            )),
            night_assignments=Count('id', filter=Q(
                shift__template__is_overnight=True
            )),
            waakdienst_assignments=Count('id', filter=Q(
                shift__template__category__name='WAAKDIENST'
            )),
            incident_assignments=Count('id', filter=Q(
                shift__template__category__name='INCIDENT'
            ))
        )
        
        # Calculate workload balance scores
        total = workload_stats['total_assignments']
        
        return {
            **workload_stats,
            'weekend_percentage': (
                (workload_stats['weekend_assignments'] / total * 100)
                if total > 0 else 0.0
            ),
            'night_percentage': (
                (workload_stats['night_assignments'] / total * 100)
                if total > 0 else 0.0
            ),
            'workload_intensity': cls._calculate_workload_intensity(assignments),
            'balance_score': cls._calculate_balance_score(workload_stats),
            'analysis_period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days * 2  # Past + future
            }
        }
    
    @classmethod
    def _calculate_workload_intensity(cls, assignments: QuerySet) -> float:
        """Calculate workload intensity based on assignment patterns"""
        if not assignments.exists():
            return 0.0
        
        # This is a simplified calculation - could be enhanced with more factors
        total_hours = sum(
            assignment.shift.template.duration_hours 
            for assignment in assignments
            if assignment.shift.template.duration_hours
        )
        total_days = assignments.count()
        
        return round(total_hours / max(total_days, 1), 2)
    
    @classmethod
    def _calculate_balance_score(cls, workload_stats: Dict[str, Any]) -> float:
        """Calculate work-life balance score (0-100)"""
        total = workload_stats['total_assignments']
        if total == 0:
            return 100.0
        
        # Penalize excessive weekend and night work
        weekend_penalty = min(workload_stats['weekend_assignments'] / total * 50, 25)
        night_penalty = min(workload_stats['night_assignments'] / total * 30, 15)
        
        # Penalize workload concentration
        intensity_penalty = min(total / 30 * 20, 20)  # Penalize more than 1 assignment per day average
        
        balance_score = 100 - weekend_penalty - night_penalty - intensity_penalty
        return max(round(balance_score, 1), 0.0)