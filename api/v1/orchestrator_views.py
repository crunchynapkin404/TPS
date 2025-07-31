"""
Planning Orchestrator API Views for TPS V1.4
New endpoints that use the improved orchestrator
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, date

from apps.teams.models import Team
from core.services.planning_orchestrator import PlanningOrchestrator, PlanningAlgorithm


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_orchestrator_planning(request):
    """Generate planning using the new orchestrator with proper weekly assignment logic"""
    try:
        data = request.data
        
        # Parse request data
        start_date_str = data.get('start_date') or data.get('period')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        weeks = int(data.get('weeks') or data.get('duration', 4))
        algorithm_str = data.get('algorithm', 'balanced')
        team_id = data.get('team_id')
        
        # Map algorithm string to enum
        algorithm_map = {
            'balanced': PlanningAlgorithm.BALANCED,
            'sequential': PlanningAlgorithm.SEQUENTIAL,
            'custom': PlanningAlgorithm.CUSTOM
        }
        algorithm = algorithm_map.get(algorithm_str, PlanningAlgorithm.BALANCED)
        
        # Get team
        if team_id:
            team = Team.objects.get(id=team_id, is_active=True)
        else:
            team = Team.objects.filter(is_active=True).first()
        
        if not team:
            return Response({
                'success': False,
                'error': 'No active team found',
                'message': 'Please specify a valid team ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create orchestrator and generate planning
        orchestrator = PlanningOrchestrator(team)
        
        # Validate prerequisites first
        validation = orchestrator.validate_prerequisites()
        if not validation.success:
            return Response({
                'success': False,
                'validation_errors': validation.errors,
                'validation_warnings': validation.warnings,
                'message': 'Prerequisites validation failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate planning
        result = orchestrator.generate_complete_planning(start_date, weeks, algorithm)
        
        if result.success:
            # Format response with weekly breakdown
            incident_assignments = result.data.get('incident_planning', {}).get('assignments', [])
            waakdienst_assignments = result.data.get('waakdienst_planning', {}).get('assignments', [])
            
            # Analyze weekly distribution for verification
            weekly_analysis = analyze_weekly_distribution(incident_assignments)
            
            return Response({
                'success': True,
                'team': team.name,
                'total_assignments': len(incident_assignments) + len(waakdienst_assignments),
                'incident_assignments': len(incident_assignments),
                'waakdienst_assignments': len(waakdienst_assignments),
                'weekly_analysis': weekly_analysis,
                'message': result.message,
                'generated_at': timezone.now().isoformat()
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': result.errors,
                'message': result.message
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Team.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Team not found',
            'message': 'The specified team does not exist'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate planning'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_orchestrator_prerequisites(request):
    """Validate prerequisites for planning generation"""
    try:
        team_id = request.GET.get('team_id')
        
        if team_id:
            team = Team.objects.get(id=team_id, is_active=True)
        else:
            team = Team.objects.filter(is_active=True).first()
        
        if not team:
            return Response({
                'success': False,
                'error': 'No active team found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        orchestrator = PlanningOrchestrator(team)
        validation = orchestrator.validate_prerequisites()
        
        return Response({
            'success': validation.success,
            'team': team.name,
            'checks': validation.checks,
            'errors': validation.errors,
            'warnings': validation.warnings,
            'message': validation.message
        })
        
    except Team.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Team not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def analyze_weekly_distribution(incident_assignments):
    """Analyze incident assignments to verify proper weekly distribution"""
    from collections import defaultdict
    from datetime import timedelta
    
    weekly_assignments = defaultdict(list)
    weekly_engineers = defaultdict(set)
    
    for assignment in incident_assignments:
        if assignment.assignment_type == 'primary':
            shift_date = assignment.shift.date
            monday = shift_date - timedelta(days=shift_date.weekday())
            week_key = monday.strftime('%Y-%m-%d')
            
            weekly_assignments[week_key].append(assignment)
            weekly_engineers[week_key].add(assignment.user.get_full_name())
    
    analysis = {
        'total_weeks': len(weekly_assignments),
        'weeks': []
    }
    
    for week, assignments in sorted(weekly_assignments.items()):
        engineers = list(weekly_engineers[week])
        analysis['weeks'].append({
            'week_start': week,
            'assignments_count': len(assignments),
            'engineers': engineers,
            'engineer_count': len(engineers),
            'correct_single_engineer': len(engineers) == 1
        })
    
    # Calculate correctness
    correct_weeks = sum(1 for week in analysis['weeks'] if week['correct_single_engineer'])
    analysis['correctness_rate'] = (correct_weeks / len(analysis['weeks']) * 100) if analysis['weeks'] else 100
    analysis['issues_found'] = len(analysis['weeks']) - correct_weeks
    
    return analysis
