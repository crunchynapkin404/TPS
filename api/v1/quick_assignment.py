"""
Quick Assignment API for Calendar
Creates shifts and assignments directly from calendar interface
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db import transaction

from apps.assignments.models import Assignment
from apps.accounts.models import User
from apps.teams.models import Team
from apps.scheduling.models import ShiftInstance, ShiftTemplate, ShiftCategory
from core.services.assignment_service import AssignmentService


@api_view(['POST'])
@permission_classes([AllowAny])  # Temporarily allow unauthenticated access for development
def quick_create_assignment(request):
    """
    Create a new assignment with automatic shift creation
    Expected data:
    {
        "user_id": 1,
        "date": "2025-07-30",
        "assignment_type": "waakdienst",
        "start_time": "09:00",
        "end_time": "17:00",
        "notes": "Optional notes",
        "team_id": 4
    }
    """
    try:
        # Extract data from request
        user_id = request.data.get('user_id')
        assignment_date = request.data.get('date')
        assignment_type = request.data.get('assignment_type', 'waakdienst')
        start_time = request.data.get('start_time', '09:00')
        end_time = request.data.get('end_time', '17:00')
        notes = request.data.get('notes', '')
        team_id = request.data.get('team_id', 4)  # Default to team 4
        
        # Validate required fields
        if not all([user_id, assignment_date, start_time, end_time]):
            return Response({
                'error': 'user_id, date, start_time, and end_time are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate team
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse date and times
        try:
            shift_date = datetime.strptime(assignment_date, '%Y-%m-%d').date()
            start_datetime = datetime.strptime(f"{assignment_date} {start_time}", '%Y-%m-%d %H:%M')
            end_datetime = datetime.strptime(f"{assignment_date} {end_time}", '%Y-%m-%d %H:%M')
            
            # Handle overnight shifts
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
            
            # Make timezone aware
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
            
        except ValueError:
            return Response({
                'error': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to get existing category, or create minimal one for manual assignments
        shift_category, created = ShiftCategory.objects.get_or_create(
            name=assignment_type.upper(),
            defaults={
                'description': f'{assignment_type.title()} assignments',
                'color': get_category_color(assignment_type),
                'max_weeks_per_year': 52,  # Default high value for manual assignments
                'is_active': True
            }
        )
        
        # Get or create shift template
        template, created = ShiftTemplate.objects.get_or_create(
            name=f'{assignment_type.title()} - {start_time} to {end_time}',
            defaults={
                'category': shift_category,
                'start_time': datetime.strptime(start_time, '%H:%M').time(),
                'end_time': datetime.strptime(end_time, '%H:%M').time(),
                'duration_hours': (end_datetime - start_datetime).total_seconds() / 3600,
                'required_skills': ['Waakdienst'] if assignment_type == 'waakdienst' else [],
                'engineers_required': 1,
                'description': f'Quick created {assignment_type} shift'
            }
        )
        
        with transaction.atomic():
            # Create shift instance
            shift = ShiftInstance.objects.create(
                template=template,
                date=shift_date,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                status='planned'
            )
            
            # Create assignment
            assignment = Assignment.objects.create(
                user=user,
                shift=shift,
                status='confirmed',
                assigned_at=timezone.now(),
                assignment_type='primary'
            )
        
        return Response({
            'success': True,
            'message': 'Assignment created successfully',
            'assignment': {
                'id': assignment.pk,
                'user_id': assignment.user.pk,
                'user_name': assignment.user.get_full_name(),
                'date': assignment.shift.date.isoformat(),
                'start_time': assignment.shift.start_datetime.strftime('%H:%M'),
                'end_time': assignment.shift.end_datetime.strftime('%H:%M'),
                'type': assignment_type,
                'status': assignment.status
            },
            'shift': {
                'id': shift.pk,
                'template_id': shift.template.pk
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create assignment: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_category_color(assignment_type):
    """Get color for assignment type"""
    color_map = {
        'waakdienst': '#10b981',    # Green
        'incident': '#ef4444',     # Red
        'changes': '#8b5cf6',      # Purple
        'maintenance': '#f59e0b',  # Orange
        'support': '#3b82f6',      # Blue
        'training': '#14b8a6',     # Teal
    }
    return color_map.get(assignment_type.lower(), '#6b7280')  # Default gray


@api_view(['GET'])
@permission_classes([AllowAny])
def assignment_types(request):
    """
    Get available assignment types for quick creation
    """
    types = [
        {
            'value': 'waakdienst',
            'label': '🛡️ Waakdienst',
            'description': 'On-call duty shifts',
            'color': '#10b981',
            'default_duration': 8
        },
        {
            'value': 'incident',
            'label': '🚨 Incident Response',
            'description': 'Emergency incident handling',
            'color': '#ef4444',
            'default_duration': 4
        },
        {
            'value': 'changes',
            'label': '⚙️ Change Management',
            'description': 'Planned system changes',
            'color': '#8b5cf6',
            'default_duration': 6
        },
        {
            'value': 'maintenance',
            'label': '🔧 Maintenance',
            'description': 'System maintenance work',
            'color': '#f59e0b',
            'default_duration': 4
        },
        {
            'value': 'support',
            'label': '💬 Support',
            'description': 'User support shifts',
            'color': '#3b82f6',
            'default_duration': 8
        },
        {
            'value': 'training',
            'label': '📚 Training',
            'description': 'Training sessions',
            'color': '#14b8a6',
            'default_duration': 2
        }
    ]
    
    return Response({
        'assignment_types': types
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_assignment_slot(request):
    """
    Validate if an assignment slot is available
    """
    try:
        user_id = request.data.get('user_id')
        assignment_date = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        # Parse datetime
        start_datetime = datetime.strptime(f"{assignment_date} {start_time}", '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(f"{assignment_date} {end_time}", '%Y-%m-%d %H:%M')
        
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)
        
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        
        # Check for conflicts
        conflicts = Assignment.objects.filter(
            user_id=user_id,
            shift__start_datetime__lt=end_datetime,
            shift__end_datetime__gt=start_datetime
        )
        
        if conflicts.exists():
            conflict_list = []
            for conflict in conflicts:
                conflict_list.append({
                    'id': conflict.pk,
                    'start_time': conflict.shift.start_datetime.strftime('%H:%M'),
                    'end_time': conflict.shift.end_datetime.strftime('%H:%M'),
                    'type': conflict.shift.template.category.name if conflict.shift.template.category else 'Unknown'
                })
            
            return Response({
                'valid': False,
                'conflicts': conflict_list,
                'message': f'User has {len(conflict_list)} conflicting assignment(s)'
            })
        
        return Response({
            'valid': True,
            'message': 'Time slot is available'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Validation failed: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
