"""
TPS V1.4 - Analytics API Views
Real-time analytics data endpoints
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F, Case, When, IntegerField
from datetime import datetime, timedelta, date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import calendar

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment
from apps.accounts.models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_overview(request):
    """
    Get comprehensive analytics overview
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    
    # Date ranges
    current_month_start = today.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    
    # Basic metrics
    total_assignments_current = Assignment.objects.filter(
        shift__start_datetime__gte=current_month_start,
        shift__start_datetime__lt=current_month_start + timedelta(days=32)
    ).count()
    
    total_assignments_last = Assignment.objects.filter(
        shift__start_datetime__gte=last_month_start,
        shift__start_datetime__lte=last_month_end
    ).count()
    
    # Calculate growth percentage
    assignment_growth = 0
    if total_assignments_last > 0:
        assignment_growth = round(((total_assignments_current - total_assignments_last) / total_assignments_last * 100), 1)
    
    # Team performance
    active_teams = Team.objects.filter(is_active=True).count()
    
    # User engagement
    active_users = User.objects.filter(
        is_active=True,
        shift_assignments__shift__start_datetime__gte=current_month_start - timedelta(days=30)
    ).distinct().count()
    
    # System efficiency
    confirmed_assignments = Assignment.objects.filter(
        shift__start_datetime__gte=current_month_start,
        status='confirmed'
    ).count()
    
    efficiency = round((confirmed_assignments / total_assignments_current * 100), 1) if total_assignments_current > 0 else 100
    
    return Response({
        'overview': {
            'total_assignments': total_assignments_current,
            'assignment_growth': assignment_growth,
            'active_teams': active_teams,
            'active_users': active_users,
            'system_efficiency': efficiency,
            'last_updated': now.isoformat()
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_workload_trends(request):
    """
    Get workload trend data for charts
    """
    now = timezone.now()
    today = now.date()
    
    # Get last 12 months of data
    monthly_data = []
    for i in range(12):
        month_start = today.replace(day=1) - timedelta(days=i*30)
        month_start = month_start.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        assignments_count = Assignment.objects.filter(
            shift__start_datetime__gte=month_start,
            shift__start_datetime__lte=month_end,
            status__in=['confirmed', 'completed']
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%B'),
            'assignments': assignments_count
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    return Response({
        'workload_trends': monthly_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_team_performance(request):
    """
    Get team performance analytics
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    current_month_start = today.replace(day=1)
    
    # Get accessible teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    team_performance = []
    
    for team in user_teams:
        # Get team assignments for current month
        team_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_month_start
        )
        
        total_assignments = team_assignments.count()
        confirmed_assignments = team_assignments.filter(status='confirmed').count()
        completed_assignments = team_assignments.filter(status='completed').count()
        
        # Calculate performance metrics
        completion_rate = round((completed_assignments / total_assignments * 100), 1) if total_assignments > 0 else 0
        confirmation_rate = round((confirmed_assignments / total_assignments * 100), 1) if total_assignments > 0 else 0
        
        # Get team members count
        members_count = TeamMembership.objects.filter(team=team, is_active=True).count()
        
        team_performance.append({
            'team_id': team.pk,
            'team_name': team.name,
            'members_count': members_count,
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'completion_rate': completion_rate,
            'confirmation_rate': confirmation_rate,
            'department': team.department
        })
    
    return Response({
        'team_performance': team_performance
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_fairness_metrics(request):
    """
    Get fairness distribution analytics
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    current_month_start = today.replace(day=1)
    
    # Get accessible teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    fairness_data = []
    
    for team in user_teams:
        # Get assignment distribution for team members
        team_members = TeamMembership.objects.filter(team=team, is_active=True)
        member_assignments = []
        
        for membership in team_members:
            assignment_count = Assignment.objects.filter(
                user=membership.user,
                shift__planning_period__teams=team,
                shift__start_datetime__gte=current_month_start,
                status__in=['confirmed', 'completed']
            ).count()
            
            member_assignments.append({
                'user_name': membership.user.get_full_name(),
                'assignment_count': assignment_count
            })
        
        # Calculate fairness score
        if member_assignments:
            assignment_counts = [m['assignment_count'] for m in member_assignments]
            avg_assignments = sum(assignment_counts) / len(assignment_counts)
            max_deviation = max(abs(count - avg_assignments) for count in assignment_counts) if assignment_counts else 0
            fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
        else:
            fairness_score = 100
            
        fairness_data.append({
            'team_id': team.pk,
            'team_name': team.name,
            'fairness_score': round(fairness_score, 1),
            'member_distribution': member_assignments
        })
    
    return Response({
        'fairness_metrics': fairness_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_system_health(request):
    """
    Get system health metrics
    """
    now = timezone.now()
    today = now.date()
    week_start = today - timedelta(days=7)
    
    # Assignment status distribution
    status_counts = Assignment.objects.filter(
        shift__start_datetime__gte=week_start
    ).values('status').annotate(count=Count('id'))
    
    status_distribution = {item['status']: item['count'] for item in status_counts}
    
    # Calculate health metrics
    total_assignments = sum(status_distribution.values())
    failed_assignments = status_distribution.get('declined', 0) + status_distribution.get('no_show', 0) + status_distribution.get('cancelled', 0)
    
    system_health = round(((total_assignments - failed_assignments) / total_assignments * 100), 1) if total_assignments > 0 else 100
    
    # Database performance (simplified)
    db_health = 99.5  # Placeholder - could implement real DB health checks
    
    # API response times (simplified)
    api_health = 98.2  # Placeholder - could implement real API monitoring
    
    return Response({
        'system_health': {
            'overall_health': system_health,
            'database_health': db_health,
            'api_health': api_health,
            'assignment_status_distribution': status_distribution,
            'total_assignments_week': total_assignments,
            'failed_assignments_week': failed_assignments,
            'last_updated': now.isoformat()
        }
    })
