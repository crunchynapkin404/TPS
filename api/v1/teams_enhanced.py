"""
TPS V1.4 - Teams API Views
Enhanced team management endpoints
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment
from apps.accounts.models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teams_overview(request):
    """
    Get enhanced teams overview with statistics
    """
    user = request.user
    
    # Get teams user has access to
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user) | Q(memberships__user__is_staff=True)
    ).distinct()
    
    teams_data = []
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    for team in user_teams:
        # Get team member count
        member_count = TeamMembership.objects.filter(team=team, is_active=True).count()
        
        # Get current week assignments
        week_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__date__gte=week_start,
            shift__start_datetime__date__lte=week_end,
            status__in=['confirmed', 'pending_confirmation']
        ).count()
        
        # Calculate workload percentage
        max_assignments_per_member = 7  # Assume max 1 per day
        max_team_assignments = member_count * max_assignments_per_member
        workload_percentage = (week_assignments / max_team_assignments * 100) if max_team_assignments > 0 else 0
        
        # Get team performance metrics
        monthly_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__date__gte=today.replace(day=1),
            status__in=['confirmed', 'completed']
        ).count()
        
        teams_data.append({
            'id': team.pk,
            'name': team.name,
            'description': team.description,
            'department': team.department,
            'location': team.location,
            'member_count': member_count,
            'team_leader': team.team_leader.get_full_name() if team.team_leader else None,
            'is_active': team.is_active,
            'workload_percentage': min(round(workload_percentage, 1), 100),
            'workload_status': 'high' if workload_percentage > 85 else 'medium' if workload_percentage > 60 else 'low',
            'weekly_assignments': week_assignments,
            'monthly_assignments': monthly_assignments,
            'allows_auto_assignment': team.allows_auto_assignment
        })
    
    return Response({
        'teams': teams_data,
        'total_teams': len(teams_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members(request, team_id):
    """
    Get detailed team member information
    """
    try:
        team = Team.objects.get(pk=team_id)
        
        # Check user has access to this team
        user = request.user
        if not (user.is_staff or 
                TeamMembership.objects.filter(team=team, user=user).exists() or 
                team.team_leader == user):
            return Response({'error': 'Access denied'}, status=403)
        
        members = TeamMembership.objects.filter(
            team=team, is_active=True
        ).select_related('user', 'role').order_by('user__last_name')
        
        members_data = []
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        for membership in members:
            # Get member's assignment count this month
            monthly_assignments = Assignment.objects.filter(
                user=membership.user,
                shift__start_datetime__date__gte=month_start,
                status__in=['confirmed', 'completed']
            ).count()
            
            # Get next upcoming assignment
            next_assignment = Assignment.objects.filter(
                user=membership.user,
                shift__start_datetime__gt=timezone.now(),
                status__in=['confirmed', 'pending_confirmation']
            ).select_related('shift__template').first()
            
            members_data.append({
                'user_id': membership.user.pk,
                'name': membership.user.get_full_name(),
                'email': membership.user.email,
                'role': membership.role.name,
                'join_date': membership.join_date.isoformat(),
                'is_primary_team': membership.is_primary_team,
                'availability_percentage': membership.availability_percentage,
                'monthly_assignments': monthly_assignments,
                'next_assignment': {
                    'shift_name': next_assignment.shift.template.name,
                    'start_time': next_assignment.shift.start_datetime.isoformat()
                } if next_assignment else None,
                'preferences': {
                    'waakdienst': membership.prefers_waakdienst,
                    'incident': membership.prefers_incident,
                    'weekend': membership.weekend_availability,
                    'night_shift': membership.night_shift_availability
                }
            })
        
        return Response({
            'team': {
                'id': team.pk,
                'name': team.name,
                'description': team.description
            },
            'members': members_data,
            'member_count': len(members_data)
        })
        
    except Team.DoesNotExist:
        return Response({'error': 'Team not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_statistics(request):
    """
    Get overall team statistics
    """
    user = request.user
    
    # Get accessible teams
    all_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user) | Q(memberships__user__is_staff=True)
    ).distinct()
    
    total_teams = all_teams.count()
    active_teams = all_teams.filter(is_active=True).count()
    
    # Get total members across all teams
    total_members = User.objects.filter(
        team_memberships__team__in=all_teams,
        is_active=True
    ).distinct().count()
    
    # Get assignments this month
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    monthly_assignments = Assignment.objects.filter(
        shift__planning_period__teams__in=all_teams,
        shift__start_datetime__date__gte=month_start,
        status__in=['confirmed', 'completed']
    ).count()
    
    # Calculate average team size
    avg_team_size = total_members / active_teams if active_teams > 0 else 0
    
    # Get department breakdown
    departments = all_teams.values('department').annotate(
        team_count=Count('id')
    ).order_by('-team_count')
    
    return Response({
        'overview': {
            'total_teams': total_teams,
            'active_teams': active_teams,
            'total_members': total_members,
            'monthly_assignments': monthly_assignments,
            'avg_team_size': round(avg_team_size, 1)
        },
        'departments': list(departments)
    })
