"""
TPS V1.4 - Analytics API Views
Comprehensive analytics and reporting endpoints
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F, Case, When, IntegerField
from datetime import datetime, timedelta, date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment
from apps.accounts.models import User
from apps.scheduling.models import ShiftInstance, PlanningPeriod


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_overview(request):
    """
    Get comprehensive analytics overview
    """
    user = request.user
    period = request.GET.get('period', 'month')  # week, month, quarter, year
    
    # Calculate date ranges
    now = timezone.now()
    today = now.date()
    
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period == 'quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (quarter - 1) * 3 + 1, 1)
        end_date = date(today.year, quarter * 3 + 1, 1) - timedelta(days=1) if quarter < 4 else date(today.year, 12, 31)
    else:  # year
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
    
    # Get user's teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    # Overall fairness score calculation
    assignments_in_period = Assignment.objects.filter(
        shift__start_datetime__date__gte=start_date,
        shift__start_datetime__date__lte=end_date,
        status__in=['confirmed', 'completed']
    )
    
    user_assignment_counts = assignments_in_period.values('user').annotate(
        assignment_count=Count('id')
    ).values_list('assignment_count', flat=True)
    
    if user_assignment_counts:
        avg_assignments = sum(user_assignment_counts) / len(user_assignment_counts)
        max_deviation = max(abs(count - avg_assignments) for count in user_assignment_counts) if avg_assignments > 0 else 0
        fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
    else:
        fairness_score = 100.0
    
    # Average workload calculation
    total_shifts = assignments_in_period.count()
    active_users = User.objects.filter(
        team_memberships__team__in=user_teams,
        is_active=True
    ).distinct().count()
    avg_workload = (total_shifts / active_users) if active_users > 0 else 0
    
    # Coverage rate calculation
    total_required_shifts = ShiftInstance.objects.filter(
        start_datetime__date__gte=start_date,
        start_datetime__date__lte=end_date,
        planning_period__teams__in=user_teams
    ).count()
    covered_shifts = assignments_in_period.count()
    coverage_rate = (covered_shifts / total_required_shifts * 100) if total_required_shifts > 0 else 0
    
    # Planning efficiency (assignments confirmed vs proposed)
    total_assignments = Assignment.objects.filter(
        shift__start_datetime__date__gte=start_date,
        shift__start_datetime__date__lte=end_date
    ).count()
    confirmed_assignments = Assignment.objects.filter(
        shift__start_datetime__date__gte=start_date,
        shift__start_datetime__date__lte=end_date,
        status='confirmed'
    ).count()
    planning_efficiency = (confirmed_assignments / total_assignments * 100) if total_assignments > 0 else 0
    
    return Response({
        'period': period,
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'key_metrics': {
            'fairness_score': round(fairness_score, 1),
            'average_workload': round(avg_workload, 1),
            'coverage_rate': round(coverage_rate, 1),
            'planning_efficiency': round(planning_efficiency, 1)
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_fairness_distribution(request):
    """
    Get fairness distribution data for charts
    """
    user = request.user
    period = request.GET.get('period', 'month')
    
    # Calculate date range (same logic as above)
    now = timezone.now()
    today = now.date()
    
    if period == 'month':
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Get user assignment distribution
    assignments = Assignment.objects.filter(
        shift__start_datetime__date__gte=start_date,
        shift__start_datetime__date__lte=end_date,
        status__in=['confirmed', 'completed']
    ).values('user__first_name', 'user__last_name').annotate(
        assignment_count=Count('id')
    ).order_by('-assignment_count')
    
    fairness_data = []
    for assignment in assignments:
        fairness_data.append({
            'user_name': f"{assignment['user__first_name']} {assignment['user__last_name']}",
            'assignment_count': assignment['assignment_count']
        })
    
    return Response({
        'fairness_distribution': fairness_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_workload_trends(request):
    """
    Get workload trends over time
    """
    user = request.user
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily assignment counts
    daily_assignments = []
    current_date = start_date
    
    while current_date <= end_date:
        assignments_count = Assignment.objects.filter(
            shift__start_datetime__date=current_date,
            status__in=['confirmed', 'completed']
        ).count()
        
        daily_assignments.append({
            'date': current_date.isoformat(),
            'assignments': assignments_count
        })
        current_date += timedelta(days=1)
    
    return Response({
        'workload_trends': daily_assignments
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_team_performance(request):
    """
    Get team performance analytics
    """
    user = request.user
    period = request.GET.get('period', 'month')
    
    # Get user's teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    team_performance = []
    for team in user_teams:
        # Get team assignments for period
        assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            status__in=['confirmed', 'completed']
        )
        
        # Calculate performance metrics
        total_assignments = assignments.count()
        completed_assignments = assignments.filter(status='completed').count()
        completion_rate = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        # Get team member count
        member_count = TeamMembership.objects.filter(team=team, is_active=True).count()
        
        team_performance.append({
            'team_id': team.pk,
            'team_name': team.name,
            'member_count': member_count,
            'total_assignments': total_assignments,
            'completion_rate': round(completion_rate, 1),
            'avg_assignments_per_member': round(total_assignments / member_count, 1) if member_count > 0 else 0
        })
    
    return Response({
        'team_performance': team_performance
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_top_performers(request):
    """
    Get top performing users
    """
    user = request.user
    limit = int(request.GET.get('limit', 10))
    period = request.GET.get('period', 'month')
    
    # Calculate date range
    today = timezone.now().date()
    if period == 'month':
        start_date = today.replace(day=1)
    else:
        start_date = today - timedelta(days=30)
    
    # Get top performers by assignment count
    top_performers = Assignment.objects.filter(
        shift__start_datetime__date__gte=start_date,
        status__in=['confirmed', 'completed']
    ).values(
        'user__first_name', 'user__last_name', 'user__pk'
    ).annotate(
        assignment_count=Count('id'),
        completion_rate=Count(Case(When(status='completed', then=1), output_field=IntegerField())) * 100.0 / Count('id')
    ).order_by('-assignment_count')[:limit]
    
    performers_data = []
    for performer in top_performers:
        performers_data.append({
            'user_id': performer['user__pk'],
            'user_name': f"{performer['user__first_name']} {performer['user__last_name']}",
            'assignment_count': performer['assignment_count'],
            'completion_rate': round(performer['completion_rate'], 1)
        })
    
    return Response({
        'top_performers': performers_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_alerts_insights(request):
    """
    Get system alerts and insights
    """
    user = request.user
    today = timezone.now().date()
    
    alerts = []
    
    # Check for overloaded teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    for team in user_teams:
        # Check current week workload
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__date__gte=week_start,
            shift__start_datetime__date__lte=week_end,
            status__in=['confirmed', 'pending_confirmation']
        ).count()
        
        member_count = TeamMembership.objects.filter(team=team, is_active=True).count()
        if member_count > 0:
            avg_assignments_per_member = weekly_assignments / member_count
            
            if avg_assignments_per_member > 5:
                alerts.append({
                    'type': 'warning',
                    'title': f'{team.name} Overloaded',
                    'message': f'Team has {avg_assignments_per_member:.1f} assignments per member this week',
                    'action': 'Consider redistributing workload'
                })
    
    # Check for fairness issues
    month_start = today.replace(day=1)
    monthly_assignments = Assignment.objects.filter(
        shift__start_datetime__date__gte=month_start,
        status__in=['confirmed', 'completed']
    ).values('user').annotate(assignment_count=Count('id')).values_list('assignment_count', flat=True)
    
    if monthly_assignments:
        avg_monthly = sum(monthly_assignments) / len(monthly_assignments)
        max_deviation = max(abs(count - avg_monthly) for count in monthly_assignments)
        if max_deviation > avg_monthly * 0.3:  # 30% deviation threshold
            alerts.append({
                'type': 'warning',
                'title': 'Fairness Alert',
                'message': f'Assignment distribution variance is {max_deviation/avg_monthly*100:.0f}%',
                'action': 'Review assignment distribution'
            })
    
    # Add positive insights
    coverage_this_week = Assignment.objects.filter(
        shift__start_datetime__date__gte=today - timedelta(days=today.weekday()),
        shift__start_datetime__date__lte=today - timedelta(days=today.weekday()) + timedelta(days=6),
        status__in=['confirmed', 'completed']
    ).count()
    
    if coverage_this_week > 0:
        alerts.append({
            'type': 'success',
            'title': 'Good Coverage',
            'message': f'{coverage_this_week} shifts covered this week',
            'action': 'Keep up the good work!'
        })
    
    return Response({
        'alerts': alerts
    })
