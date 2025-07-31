"""
TPS V1.4 - Dashboard API Views
Real-time dashboard data endpoints
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
    Get real-time dashboard statistics for the current user
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    
    # Get user's teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    # Upcoming shifts (next 7 days)
    upcoming_shifts = Assignment.objects.filter(
        user=user,
        shift__start_datetime__gt=now,
        shift__start_datetime__lte=now + timedelta(days=7),
        status__in=['confirmed', 'pending_confirmation']
    ).count()
    
    # Pending approvals (if user is manager/team leader)
    pending_approvals = 0
    if user.is_staff or Team.objects.filter(team_leader=user).exists():
        led_teams = Team.objects.filter(team_leader=user)
        pending_approvals = Assignment.objects.filter(
            shift__planning_period__teams__in=led_teams,
            status='pending_confirmation'
        ).count()
    
    # Active team members count
    active_members = User.objects.filter(
        team_memberships__team__in=user_teams,
        is_active=True
    ).distinct().count()
    
    # Total assignments this month
    monthly_assignments = Assignment.objects.filter(
        user=user,
        shift__start_datetime__gte=month_start,
        shift__start_datetime__lt=month_start + timedelta(days=32),
        status__in=['confirmed', 'completed']
    ).count()
    
    # System health calculation
    failed_assignments = Assignment.objects.filter(
        status__in=['declined', 'no_show', 'cancelled'],
        assigned_at__gte=today - timedelta(days=7)
    ).count()
    total_assignments = Assignment.objects.filter(
        assigned_at__gte=today - timedelta(days=7)
    ).count()
    system_health = 100.0 if total_assignments == 0 else ((total_assignments - failed_assignments) / total_assignments) * 100
    
    # Fairness score calculation
    try:
        user_assignment_counts = Assignment.objects.filter(
            shift__start_datetime__gte=month_start,
            status__in=['confirmed', 'completed']
        ).values('user').annotate(
            assignment_count=Count('id')
        ).values_list('assignment_count', flat=True)
        
        if user_assignment_counts:
            avg_assignments = sum(user_assignment_counts) / len(user_assignment_counts)
            max_deviation = max(abs(count - avg_assignments) for count in user_assignment_counts)
            fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
        else:
            fairness_score = 100.0
    except Exception:
        fairness_score = 85.0
    
    return Response({
        'my_upcoming_shifts': upcoming_shifts,
        'pending_approvals': pending_approvals,
        'active_members': active_members,
        'monthly_assignments': monthly_assignments,
        'system_health': round(system_health, 1),
        'fairness_score': round(fairness_score, 1),
        'timestamp': now.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_recent_activity(request):
    """
    Get recent activity for dashboard
    """
    user = request.user
    limit = int(request.GET.get('limit', 10))
    
    # Get user's teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    # Recent assignments
    recent_assignments = Assignment.objects.filter(
        Q(user=user) | Q(shift__planning_period__teams__in=user_teams)
    ).select_related(
        'user', 'shift__template', 'shift__template__category'
    ).order_by('-assigned_at')[:limit]
    
    activity_data = []
    for assignment in recent_assignments:
        activity_data.append({
            'id': assignment.assignment_id,
            'user_name': assignment.user.get_full_name(),
            'shift_name': assignment.shift.template.name,
            'start_time': assignment.shift.start_datetime.isoformat(),
            'end_time': assignment.shift.end_datetime.isoformat(),
            'status': assignment.status,
            'assigned_at': assignment.assigned_at.isoformat()
        })
    
    return Response({
        'recent_activity': activity_data,
        'count': len(activity_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_team_overview(request):
    """
    Get team overview data for dashboard
    """
    user = request.user
    today = timezone.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    
    # Get user's teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    teams_data = []
    for team in user_teams:
        # Get current week assignments for this team
        team_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_week_start,
            shift__start_datetime__lte=current_week_end,
            status__in=['confirmed', 'pending_confirmation']
        ).count()
        
        # Calculate team capacity
        team_members_count = TeamMembership.objects.filter(team=team, is_active=True).count()
        team_capacity = team_members_count * 5  # Assuming 5 shifts per week max per member
        workload_percentage = (team_assignments / team_capacity * 100) if team_capacity > 0 else 0
        
        teams_data.append({
            'id': team.pk,
            'name': team.name,
            'members_count': team_members_count,
            'assignments_count': team_assignments,
            'workload_percentage': min(round(workload_percentage, 1), 100),
            'workload_status': 'danger' if workload_percentage > 90 else 'warning' if workload_percentage > 70 else 'success'
        })
    
    return Response({
        'teams': teams_data,
        'total_teams': len(teams_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_my_shifts(request):
    """
    Get user's upcoming shifts
    """
    user = request.user
    limit = int(request.GET.get('limit', 5))
    
    upcoming_shifts = Assignment.objects.filter(
        user=user,
        shift__start_datetime__gt=timezone.now(),
        status__in=['confirmed', 'pending_confirmation']
    ).select_related(
        'shift__template', 'shift__template__category'
    ).order_by('shift__start_datetime')[:limit]
    
    shifts_data = []
    for assignment in upcoming_shifts:
        shifts_data.append({
            'id': assignment.assignment_id,
            'shift_name': assignment.shift.template.name,
            'start_time': assignment.shift.start_datetime.isoformat(),
            'end_time': assignment.shift.end_datetime.isoformat(),
            'status': assignment.status,
            'category': assignment.shift.template.category.name if assignment.shift.template.category else 'General'
        })
    
    return Response({
        'upcoming_shifts': shifts_data,
        'count': len(shifts_data)
    })
