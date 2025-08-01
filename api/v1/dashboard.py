"""
TPS V1.4 - Dashboard API Views
Real-time dashboard data endpoints using service layer
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment
from apps.accounts.models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get real-time dashboard statistics for the current user using service layer
    OPTIMIZED with caching and query optimization
    """
    from core.services import DashboardService
    from core.services.cache_service import CacheService
    
    try:
        # Try to get cached dashboard data first
        cached_response = CacheService.get_dashboard_data(
            request.user.id, 
            f"api_{request.user.role}"
        )
        
        if cached_response:
            return Response(cached_response, status=status.HTTP_200_OK)
        
        # Use the dashboard service to get context
        dashboard_context = DashboardService.get_dashboard_context(request.user)
        
        # Extract relevant stats for API response
        api_response = {
            'dashboard_type': dashboard_context.get('dashboard_type', 'user'),
            'user_role': request.user.role,
            'current_date': dashboard_context.get('today'),
            'week_range': {
                'start': dashboard_context.get('week_start'),
                'end': dashboard_context.get('week_end')
            }
        }
        
        # Add role-specific stats
        if dashboard_context.get('dashboard_type') == 'admin':
            api_response.update({
                'total_users': dashboard_context.get('total_users', 0),
                'total_teams': dashboard_context.get('total_teams', 0),
                'system_health': dashboard_context.get('system_health', 100),
                'pending_leave_requests': dashboard_context.get('pending_leave_requests', 0),
                'user_engagement_rate': dashboard_context.get('user_engagement_rate', 0),
                'team_utilization_rate': dashboard_context.get('team_utilization_rate', 0),
            })
        elif dashboard_context.get('dashboard_type') == 'manager':
            api_response.update({
                'managed_teams_count': dashboard_context.get('total_managed_teams', 0),
                'pending_approvals_count': len(dashboard_context.get('pending_approvals', [])),
                'pending_leave_approvals_count': len(dashboard_context.get('pending_leave_approvals', [])),
            })
        elif dashboard_context.get('dashboard_type') == 'planner':
            api_response.update({
                'planning_periods_count': len(dashboard_context.get('planning_periods', [])),
                'unassigned_shifts_count': len(dashboard_context.get('unassigned_shifts', [])),
                'advice_count': len(dashboard_context.get('planning_advice', [])),
            })
        else:  # user
            assignment_stats = dashboard_context.get('assignment_stats', {})
            api_response.update({
                'upcoming_shifts_count': assignment_stats.get('upcoming_assignments', 0),
                'pending_confirmations': assignment_stats.get('pending_confirmations', 0),
                'this_week_assignments': assignment_stats.get('this_week_assignments', 0),
                'leave_requests_count': len(dashboard_context.get('my_leave_requests', [])),
                'total_working_today': dashboard_context.get('total_working_today', 0),
                'incident_engineer_assigned': dashboard_context.get('incident_engineer_today') is not None,
                'waakdienst_engineer_assigned': dashboard_context.get('waakdienst_engineer_today') is not None,
            })
        
        # Cache the API response
        CacheService.set_dashboard_data(
            request.user.id, 
            f"api_{request.user.role}", 
            api_response
        )
        
        return Response(api_response, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve dashboard stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_stats(request):
    """
    Get user profile statistics using UserService
    """
    from core.services import UserService
    
    try:
        user_service = UserService(request.user)
        profile_data = user_service.get_user_profile_data()
        workload_stats = user_service.get_workload_stats(request.user, period_days=30)
        
        api_response = {
            'user_info': {
                'full_name': request.user.get_full_name(),
                'employee_id': request.user.employee_id,
                'role': request.user.role,
            },
            'ytd_stats': profile_data['ytd_stats'],
            'workload_stats': workload_stats,
            'permissions': profile_data['role_permissions'],
            'teams_count': profile_data['teams'].count(),
            'skills_count': profile_data['skills'].count(),
            'recent_assignments_count': len(profile_data['recent_assignments']),
        }
        
        return Response(api_response, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve profile stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_recent_activity(request):
    """
    Get recent activity for dashboard using service layer
    """
    from core.services import DashboardService
    
    try:
        dashboard_context = DashboardService.get_dashboard_context(request.user)
        recent_activity = dashboard_context.get('recent_activity', [])
        
        # Format for API response
        formatted_activity = []
        for activity in recent_activity:
            formatted_activity.append({
                'id': activity.id,
                'user_name': activity.user.get_full_name(),
                'shift_name': activity.shift.template.name,
                'assigned_at': activity.assigned_at.isoformat(),
                'status': activity.status,
            })
        
        return Response({
            'recent_activity': formatted_activity
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve recent activity: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_team_overview(request):
    """
    Get team overview for dashboard
    """
    from core.services import PermissionService
    
    try:
        user_teams = PermissionService.get_user_teams(request.user)
        
        team_data = []
        for team in user_teams:
            team_data.append({
                'id': team.id,
                'name': team.name,
                'department': team.department,
                'member_count': team.get_member_count(),
                'is_leader': team.team_leader == request.user,
            })
        
        return Response({
            'teams': team_data,
            'total_teams': len(team_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve team overview: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_my_shifts(request):
    """
    Get user's shifts for dashboard
    """
    from core.services import UserService
    
    try:
        user_service = UserService(request.user)
        profile_data = user_service.get_user_profile_data()
        
        # Get upcoming shifts from recent assignments
        upcoming_shifts = Assignment.objects.filter(
            user=request.user,
            shift__start_datetime__gt=timezone.now()
        ).select_related('shift__template').order_by('shift__start_datetime')[:5]
        
        shifts_data = []
        for assignment in upcoming_shifts:
            shifts_data.append({
                'id': assignment.id,
                'shift_name': assignment.shift.template.name,
                'start_datetime': assignment.shift.start_datetime.isoformat(),
                'end_datetime': assignment.shift.end_datetime.isoformat(),
                'status': assignment.status,
                'category': assignment.shift.template.category.name,
            })
        
        return Response({
            'upcoming_shifts': shifts_data,
            'ytd_stats': profile_data['ytd_stats']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve user shifts: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )