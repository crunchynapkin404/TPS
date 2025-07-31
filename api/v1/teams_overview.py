"""
TPS V1.4 - Teams Overview API Views
Real-time teams data endpoints for frontend
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, F
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
def teams_overview(request):
    """
    Get comprehensive teams overview data
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    
    # Get user's accessible teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    teams_data = []
    total_active_members = 0
    active_teams = 0
    total_efficiency = 0
    
    for team in user_teams:
        # Get team memberships
        memberships = TeamMembership.objects.filter(team=team, is_active=True)
        members_count = memberships.count()
        total_active_members += members_count
        
        # Calculate team workload for current week
        team_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_week_start,
            shift__start_datetime__lte=current_week_end,
            status__in=['confirmed', 'pending_confirmation']
        ).count()
        
        team_capacity = members_count * 5  # Assuming 5 shifts per week max
        workload_percentage = (team_assignments / team_capacity * 100) if team_capacity > 0 else 0
        
        # Calculate efficiency (simplified: confirmed assignments / total assignments)
        total_team_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_week_start - timedelta(days=7),
            shift__start_datetime__lte=current_week_end
        ).count()
        
        confirmed_assignments = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_week_start - timedelta(days=7),
            shift__start_datetime__lte=current_week_end,
            status='confirmed'
        ).count()
        
        efficiency = (confirmed_assignments / total_team_assignments * 100) if total_team_assignments > 0 else 100
        total_efficiency += efficiency
        
        # Calculate fairness score (simplified)
        member_assignment_counts = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=current_week_start - timedelta(days=30),
            status__in=['confirmed', 'completed']
        ).values('user').annotate(count=Count('id')).values_list('count', flat=True)
        
        if member_assignment_counts:
            avg_assignments = sum(member_assignment_counts) / len(member_assignment_counts)
            max_deviation = max(abs(count - avg_assignments) for count in member_assignment_counts)
            fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
        else:
            fairness_score = 100
        
        # Determine team status
        if workload_percentage > 90:
            status_text = "High Load"
            workload_status = "danger"
        elif workload_percentage > 70:
            status_text = "Attention"
            workload_status = "warning" 
        else:
            status_text = "Active"
            workload_status = "success"
            
        if members_count > 0 and efficiency > 50:
            active_teams += 1
        
        # Get team members data
        members = []
        for membership in memberships:
            members.append({
                'id': membership.user.pk,
                'name': membership.user.get_full_name(),
                'email': membership.user.email,
                'role': membership.role.name if membership.role else 'member',
                'avatar_url': None,  # Placeholder for avatar
                'is_online': True,  # Simplified - you could implement real online status
            })
        
        teams_data.append({
            'id': team.pk,
            'name': team.name,
            'description': team.description,
            'department': team.department,
            'location': team.location,
            'members_count': members_count,
            'members': members,
            'workload_percentage': round(workload_percentage, 1),
            'workload_status': workload_status,
            'efficiency': round(efficiency, 1),
            'fairness_score': round(fairness_score, 1),
            'status': status_text,
            'team_leader': {
                'name': team.team_leader.get_full_name() if team.team_leader else 'No Leader',
                'email': team.team_leader.email if team.team_leader else ''
            },
            'assignments_this_week': team_assignments,
            'contact_email': team.contact_email,
            'contact_phone': team.contact_phone,
            'is_active': team.is_active,
        })
    
    avg_efficiency_rate = round(total_efficiency / len(user_teams), 1) if user_teams.exists() else 0
    
    return Response({
        'success': True,
        'teams': teams_data,
        'total_active_members': total_active_members,
        'active_teams': active_teams,
        'avg_efficiency_rate': avg_efficiency_rate,
        'timestamp': now.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teams_statistics(request):
    """
    Get team statistics for analytics
    """
    now = timezone.now()
    today = now.date()
    
    # Calculate overall statistics
    total_teams = Team.objects.filter(is_active=True).count()
    total_members = User.objects.filter(is_active=True, team_memberships__isnull=False).distinct().count()
    
    # Calculate average coverage (simplified)
    month_start = today.replace(day=1)
    total_shifts_needed = Assignment.objects.filter(
        shift__start_datetime__gte=month_start,
        shift__start_datetime__lt=month_start + timedelta(days=32)
    ).count()
    
    covered_shifts = Assignment.objects.filter(
        shift__start_datetime__gte=month_start,
        shift__start_datetime__lt=month_start + timedelta(days=32),
        status__in=['confirmed', 'completed']
    ).count()
    
    avg_coverage = round((covered_shifts / total_shifts_needed * 100), 1) if total_shifts_needed > 0 else 100
    
    # Calculate average fairness
    team_fairness_scores = []
    for team in Team.objects.filter(is_active=True):
        member_assignment_counts = Assignment.objects.filter(
            shift__planning_period__teams=team,
            shift__start_datetime__gte=month_start,
            status__in=['confirmed', 'completed']
        ).values('user').annotate(count=Count('id')).values_list('count', flat=True)
        
        if member_assignment_counts:
            avg_assignments = sum(member_assignment_counts) / len(member_assignment_counts)
            max_deviation = max(abs(count - avg_assignments) for count in member_assignment_counts)
            fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
            team_fairness_scores.append(fairness_score)
    
    avg_fairness = round(sum(team_fairness_scores) / len(team_fairness_scores), 1) if team_fairness_scores else 100
    
    # Calculate average hours per member
    total_hours = Assignment.objects.filter(
        shift__start_datetime__gte=month_start,
        shift__start_datetime__lt=month_start + timedelta(days=32),
        status__in=['confirmed', 'completed']
    ).aggregate(
        total_hours=Sum(F('shift__end_datetime') - F('shift__start_datetime'))
    )['total_hours']
    
    avg_hours = round((total_hours.total_seconds() / 3600) / total_members, 1) if total_hours and total_members > 0 else 0
    
    return Response({
        'success': True,
        'statistics': {
            'total_teams': total_teams,
            'total_members': total_members,
            'avg_coverage': avg_coverage,
            'avg_fairness': avg_fairness,
            'avg_hours': avg_hours,
            'active_teams_count': Team.objects.filter(is_active=True).count(),
            'trends': {
                'members_trend': '+5%',  # Placeholder - could calculate real trends
                'coverage_trend': '+2%',
                'fairness_trend': '+1%',
                'hours_trend': '-1%'
            }
        },
        'timestamp': now.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members(request, team_id):
    """
    Get team members for a specific team
    """
    user = request.user
    
    try:
        # Check if user has access to this team
        team = Team.objects.get(id=team_id)
        
        # Verify user has access to this team (check membership or leadership)
        if not (TeamMembership.objects.filter(team=team, user=user, is_active=True).exists() or 
                team.team_leader == user):
            return Response({
                'success': False,
                'error': 'Access denied to this team'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get active team members
        memberships = TeamMembership.objects.filter(
            team=team, 
            is_active=True
        ).select_related('user', 'role')
        
        members_data = []
        for membership in memberships:
            user_obj = membership.user
            
            # Check if user is currently online/active (simplified check)
            is_active = user_obj.last_login and (
                timezone.now() - user_obj.last_login
            ).days < 7  # Consider active if logged in within 7 days
            
            members_data.append({
                'id': user_obj.id,
                'first_name': user_obj.first_name,
                'last_name': user_obj.last_name,
                'email': user_obj.email,
                'role': membership.role.name if membership.role else 'Member',
                'is_active': is_active,
                'join_date': membership.join_date.isoformat() if membership.join_date else None,
                'availability_percentage': membership.availability_percentage,
                'skills': list(user_obj.skills.values_list('name', flat=True)) if hasattr(user_obj, 'skills') else []
            })
        
        return Response({
            'success': True,
            'team_id': team_id,
            'team_name': team.name,
            'members': members_data,
            'total_members': len(members_data),
            'timestamp': timezone.now().isoformat()
        })
        
    except Team.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Team not found',
            'team_id': team_id
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': 'An error occurred while fetching team members',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
