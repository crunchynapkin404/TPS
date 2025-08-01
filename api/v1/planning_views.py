"""
Planning API Views for TPS V1.4
Handles planning generation and management endpoints
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, date

from apps.teams.models import Team, TeamMembership
from apps.scheduling.models import ShiftTemplate, ShiftInstance, PlanningPeriod
from apps.assignments.models import Assignment
from core.services.incident_planning_service import IncidentPlanningService
from core.services.waakdienst_planning_service import WaakdienstPlanningService
from core.services.planning_orchestrator import PlanningOrchestrator, PlanningAlgorithm


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_planning(request):
    """Generate optimized shift planning using the new orchestrator"""
    try:
        data = request.data
        
        # Parse request data
        start_date = datetime.strptime(data.get('period'), '%Y-%m-%d').date()
        duration_weeks = int(data.get('duration', 2))
        algorithm_str = data.get('algorithm', 'balanced')
        team_ids = data.get('teams', [])
        shift_type = data.get('shift_type')  # Get the shift type from frontend
        
        # Map algorithm string to enum
        algorithm_map = {
            'balanced': PlanningAlgorithm.BALANCED,
            'sequential': PlanningAlgorithm.SEQUENTIAL,
            'custom': PlanningAlgorithm.CUSTOM
        }
        algorithm = algorithm_map.get(algorithm_str, PlanningAlgorithm.BALANCED)
        
        # Calculate end date
        end_date = start_date + timedelta(weeks=duration_weeks)
        
        # Create planning period for tracking
        period_name = f'Generated Planning {start_date.strftime("%Y-%m-%d")}'
        planning_period = PlanningPeriod.objects.create(
            name=period_name,
            period_type='custom',
            start_date=start_date,
            end_date=end_date,
            planning_deadline=timezone.now() + timedelta(days=7),
            status='published',
            allows_auto_generation=True,
            created_by=request.user
        )
        
        # Get teams to plan for
        if not team_ids:
            teams = Team.objects.filter(is_active=True)
        else:
            teams = Team.objects.filter(id__in=team_ids, is_active=True)
        
        total_assignments = 0
        all_results = []
        
        # Generate planning for each team using individual services based on shift_type
        for team in teams:
            # Associate team with planning period
            planning_period.teams.add(team)
            
            waakdienst_assignments = []
            incident_assignments = []
            
            # Generate only the requested shift type
            if shift_type == 'waakdienst':
                waakdienst_service = WaakdienstPlanningService(team)
                waakdienst_result = waakdienst_service.generate_waakdienst_planning(
                    start_date, duration_weeks, algorithm.value
                )
                if waakdienst_result.success:
                    waakdienst_assignments = waakdienst_result.data.get('assignments', [])
                else:
                    all_results.append({
                        'team': team.name,
                        'success': False,
                        'errors': waakdienst_result.errors,
                        'message': waakdienst_result.message
                    })
                    continue
                    
            elif shift_type == 'incident' or shift_type == 'incident-standby':
                incident_service = IncidentPlanningService(team)
                # Determine if standby should be included
                include_standby = shift_type == 'incident-standby'
                incident_result = incident_service.generate_incident_planning(
                    start_date, duration_weeks, algorithm.value, include_standby=include_standby
                )
                if incident_result.success:
                    incident_assignments = incident_result.data.get('assignments', [])
                else:
                    all_results.append({
                        'team': team.name,
                        'success': False,
                        'errors': incident_result.errors,
                        'message': incident_result.message
                    })
                    continue
            else:
                # If no shift_type specified or invalid, generate both (backward compatibility)
                orchestrator = PlanningOrchestrator(team)
                result = orchestrator.generate_complete_planning(start_date, duration_weeks, algorithm)
                
                if result.success:
                    waakdienst_assignments = result.data.get('waakdienst_planning', {}).get('assignments', [])
                    incident_assignments = result.data.get('incident_planning', {}).get('assignments', [])
                else:
                    all_results.append({
                        'team': team.name,
                        'success': False,
                        'errors': result.errors,
                        'message': result.message
                    })
                    continue
            
            # Update shift instances with planning period for all assignments
            for assignment in waakdienst_assignments + incident_assignments:
                if assignment.shift:
                    assignment.shift.planning_period = planning_period
                    assignment.shift.save()
            
            team_total = len(waakdienst_assignments) + len(incident_assignments)
            total_assignments += team_total
            
            all_results.append({
                'team': team.name,
                'success': True,
                'assignments': team_total,
                'waakdienst': len(waakdienst_assignments),
                'incident': len(incident_assignments),
                'shift_type': shift_type or 'both'
            })
        
        # Calculate overall success
        successful_teams = [r for r in all_results if r['success']]
        overall_success = len(successful_teams) > 0
        
        return Response({
            'success': overall_success,
            'planning_period_id': planning_period.id,
            'total_assignments': total_assignments,
            'teams_processed': len(teams),
            'successful_teams': len(successful_teams),
            'team_results': all_results,
            'message': f'Successfully generated {total_assignments} assignments for {len(successful_teams)}/{len(teams)} teams'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate planning'
        }, status=status.HTTP_400_BAD_REQUEST)


def generate_team_planning(team, start_date, end_date, planning_period, algorithm):
    """Generate planning for a specific team"""
    assignments = []
    
    try:
        # Generate incident assignments
        incident_service = IncidentPlanningService(team)
        incident_assignments = incident_service.generate_planning(
            start_date, 
            end_date,
            planning_period
        )
        assignments.extend(incident_assignments)
        
        # Generate waakdienst assignments
        waakdienst_service = WaakdienstPlanningService(team)
        waakdienst_assignments = waakdienst_service.generate_planning(
            start_date,
            end_date, 
            planning_period
        )
        assignments.extend(waakdienst_assignments)
        
    except Exception as e:
        print(f"Error generating planning for team {team.name}: {e}")
        # Generate fallback assignments
        assignments = generate_fallback_planning(team, start_date, end_date, planning_period)
    
    return assignments


def generate_fallback_planning(team, start_date, end_date, planning_period):
    """Generate basic planning when services fail"""
    assignments = []
    
    # Get team members
    members = team.get_active_members()
    if not members:
        return assignments
    
    # Get shift templates
    incident_template = ShiftTemplate.objects.filter(
        category__name='INCIDENT',
        is_active=True
    ).first()
    
    waakdienst_template = ShiftTemplate.objects.filter(
        category__name='WAAKDIENST', 
        is_active=True
    ).first()
    
    # Plan week by week instead of day by day
    current_date = start_date
    member_index = 0
    
    while current_date <= end_date:
        # Find the Monday of the current week
        monday = current_date - timedelta(days=current_date.weekday())
        
        # Skip if we already processed this week
        if monday < current_date:
            current_date += timedelta(days=1)
            continue
        
        # Select one member for the entire week
        weekly_member = members[member_index % len(members)]
        
        # Create incident shifts for Monday-Friday of this week
        if incident_template:
            for day_offset in range(5):  # Monday(0) to Friday(4)
                week_day = monday + timedelta(days=day_offset)
                
                # Skip if this day is outside our planning period
                if week_day < start_date or week_day > end_date:
                    continue
                
                shift_instance = ShiftInstance.objects.create(
                    template=incident_template,
                    date=week_day,
                    start_datetime=timezone.make_aware(
                        datetime.combine(week_day, incident_template.start_time)
                    ),
                    end_datetime=timezone.make_aware(
                        datetime.combine(week_day, incident_template.end_time)
                    ),
                    status='published',
                    planning_period=planning_period
                )
                
                assignment = Assignment.objects.create(
                    user=weekly_member.user,
                    shift=shift_instance,
                    status='confirmed',
                    assigned_by=None,
                    auto_assigned=True,
                    assignment_notes=f'auto_generated_week_{monday.strftime("%Y-%m-%d")}'
                )
                
                assignments.append(assignment)
        
        # Create waakdienst shifts for weekend of this week
        if waakdienst_template:
            for day_offset in range(5, 7):  # Saturday(5) and Sunday(6)
                weekend_day = monday + timedelta(days=day_offset)
                
                # Skip if this day is outside our planning period
                if weekend_day < start_date or weekend_day > end_date:
                    continue
                
                shift_instance = ShiftInstance.objects.create(
                    template=waakdienst_template,
                    date=weekend_day,
                    start_datetime=timezone.make_aware(
                        datetime.combine(weekend_day, waakdienst_template.start_time)
                    ),
                    end_datetime=timezone.make_aware(
                        datetime.combine(weekend_day, waakdienst_template.end_time)
                    ),
                    status='published',
                    planning_period=planning_period
                )
                
                assignment = Assignment.objects.create(
                    user=weekly_member.user,
                    shift=shift_instance,
                    status='confirmed',
                    assigned_by=None,
                    auto_assigned=True,
                    assignment_notes=f'auto_generated_weekend_{monday.strftime("%Y-%m-%d")}'
                )
                
                assignments.append(assignment)
        
        # Move to next week and next member
        current_date = monday + timedelta(days=7)
        member_index += 1
    
    return assignments


def calculate_planning_stats(assignments, teams):
    """Calculate planning statistics"""
    total_assignments = len(assignments)
    total_members = sum(team.get_member_count() for team in teams)
    
    if total_members == 0:
        return {
            'total_assignments': 0,
            'coverage_rate': 0,
            'fairness_score': 0,
            'conflicts': 0
        }
    
    # Calculate average assignments per member
    avg_assignments = total_assignments / total_members if total_members > 0 else 0
    
    # Simple fairness calculation (more sophisticated in real implementation)
    fairness_score = max(0, 100 - (abs(avg_assignments - 10) * 5))
    
    # Coverage rate (assuming we planned for what we needed)
    coverage_rate = min(100, (total_assignments / max(1, total_assignments)) * 100)
    
    return {
        'total_assignments': total_assignments,
        'coverage_rate': round(coverage_rate),
        'fairness_score': round(fairness_score),
        'conflicts': 0,  # Would be calculated by checking overlaps
        'avg_assignments_per_member': round(avg_assignments, 1)
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_teams(request):
    """Get available teams for planning"""
    teams = Team.objects.filter(is_active=True).prefetch_related('memberships__user')
    
    team_data = []
    for team in teams:
        team_data.append({
            'id': team.id,
            'name': team.name,
            'department': team.department,
            'member_count': team.get_member_count(),
            'description': team.description
        })
    
    return Response({
        'teams': team_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def planning_preview(request, planning_id):
    """Get detailed preview of generated planning"""
    try:
        planning_period = PlanningPeriod.objects.get(id=planning_id)
        assignments = Assignment.objects.filter(
            shift_instance__planning_period=planning_period
        ).select_related('user', 'shift_instance__template')
        
        preview_data = {
            'period': {
                'name': planning_period.name,
                'start_date': planning_period.start_date,
                'end_date': planning_period.end_date,
                'status': planning_period.status
            },
            'assignments': [
                {
                    'user': assignment.user.get_full_name(),
                    'shift_type': assignment.shift_instance.template.name,
                    'date': assignment.shift_instance.date,
                    'start_time': assignment.shift_instance.start_datetime,
                    'end_time': assignment.shift_instance.end_datetime,
                    'status': assignment.status
                }
                for assignment in assignments
            ],
            'total_assignments': len(assignments)
        }
        
        return Response(preview_data)
        
    except PlanningPeriod.DoesNotExist:
        return Response({
            'error': 'Planning period not found'
        }, status=status.HTTP_404_NOT_FOUND)
