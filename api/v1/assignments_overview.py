"""
TPS V1.4 - Assignment Management API Views
Real-time assignment data for management interface
"""

from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.teams.models import Team, TeamMembership
from apps.assignments.models import Assignment, AssignmentHistory
from apps.accounts.models import User
from apps.scheduling.models import ShiftInstance


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assignments_overview(request):
    """
    Get comprehensive assignments overview with statistics
    """
    try:
        user = request.user
        now = timezone.now()
        today = now.date()
        
        # Date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        team_filter = request.GET.get('team')
        status_filter = request.GET.get('status')
        
        # Default to current month if no dates provided
        if not start_date:
            start_date = today.replace(day=1)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        if not end_date:
            end_date = today
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get user's accessible teams
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).distinct()
        
        # Get statistics - use separate queries to avoid slice issues
        base_filter_kwargs = {
            'shift__start_datetime__gte': start_date,
            'shift__start_datetime__lte': end_date + timedelta(days=1)
        }
        
        # Build the team filter
        team_filter_q = Q(shift__planning_period__teams__in=user_teams)
        if team_filter:
            team_filter_q &= Q(shift__planning_period__teams__id=team_filter)
        
        # Build status filter
        status_filter_q = Q()
        if status_filter:
            status_filter_q = Q(status=status_filter)
        
        # Combine all filters
        combined_filter = Q(**base_filter_kwargs) & team_filter_q & status_filter_q
        
        # Get statistics with separate queries
        total_assignments = Assignment.objects.filter(combined_filter).distinct().count()
        confirmed_assignments = Assignment.objects.filter(combined_filter & Q(status='confirmed')).distinct().count()
        pending_assignments = Assignment.objects.filter(combined_filter & Q(status='pending_confirmation')).distinct().count()
        declined_assignments = Assignment.objects.filter(combined_filter & Q(status='declined')).distinct().count()
        completed_assignments = Assignment.objects.filter(combined_filter & Q(status='completed')).distinct().count()
        
        # Calculate completion rate
        completion_rate = round((completed_assignments / total_assignments * 100), 1) if total_assignments > 0 else 0
        confirmation_rate = round((confirmed_assignments / total_assignments * 100), 1) if total_assignments > 0 else 0
        
        # Get recent assignments - use a fresh query
        recent_assignments = Assignment.objects.filter(combined_filter).select_related(
            'user', 'shift__template', 'shift__planning_period'
        ).distinct().order_by('-assigned_at')[:50]
        
        assignments_data = []
        for assignment in recent_assignments:
            assignments_data.append({
                'id': str(assignment.assignment_id),
                'user': {
                    'id': assignment.user.pk,
                    'name': assignment.user.get_full_name(),
                    'email': assignment.user.email
                },
                'shift': {
                    'id': assignment.shift.pk,
                    'name': assignment.shift.template.name if assignment.shift.template else 'Unknown',
                    'start_datetime': assignment.shift.start_datetime.isoformat(),
                    'end_datetime': assignment.shift.end_datetime.isoformat(),
                    'category': assignment.shift.template.category.name if assignment.shift.template and assignment.shift.template.category else 'General'
                },
                'status': assignment.status,
                'status_display': dict(Assignment.STATUS_CHOICES).get(assignment.status, assignment.status),
                'assignment_type': assignment.assignment_type,
                'assigned_at': assignment.assigned_at.isoformat(),
                'confirmed_at': assignment.confirmed_at.isoformat() if assignment.confirmed_at else None,
                'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                'assigned_by': assignment.assigned_by.get_full_name() if assignment.assigned_by else 'System',
                'assignment_notes': assignment.assignment_notes or '',
                'can_edit': user.is_staff or assignment.assigned_by == user,
                'can_approve': user.is_staff or assignment.shift.planning_period.teams.filter(team_leader=user).exists()
            })
        
        return Response({
            'success': True,
            'overview': {
                'total_assignments': total_assignments,
                'confirmed_assignments': confirmed_assignments,
                'pending_assignments': pending_assignments,
                'overdue_assignments': declined_assignments,  # Using declined as overdue for now
                'completion_rate': completion_rate,
                'confirmation_rate': confirmation_rate
            },
            'statistics': {
                'total_assignments': total_assignments,
                'confirmed_assignments': confirmed_assignments,
                'pending_assignments': pending_assignments,
                'declined_assignments': declined_assignments,
                'completed_assignments': completed_assignments,
                'completion_rate': completion_rate,
                'confirmation_rate': confirmation_rate
            },
            'assignments': assignments_data,
            'filters': {
                'teams': [{'id': team.pk, 'name': team.name} for team in user_teams],
                'statuses': Assignment.STATUS_CHOICES
            },
            'pagination': {
                'total': total_assignments,
                'showing': len(assignments_data),
                'has_more': total_assignments > 50
            },
            'timestamp': now.isoformat()
        })
    
    except Exception as e:
        import traceback
        return Response({
            'success': False,
            'error': f'Failed to fetch assignments overview: {str(e)}',
            'traceback': traceback.format_exc()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assignments_timeline(request, assignment_id):
    """
    Get assignment timeline/history for a specific assignment
    """
    try:
        assignment = Assignment.objects.get(assignment_id=assignment_id)
        
        # Check permissions
        user = request.user
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).distinct()
        
        if not assignment.shift.planning_period.teams.filter(id__in=user_teams).exists():
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get assignment history
        history = AssignmentHistory.objects.filter(
            assignment=assignment
        ).order_by('-timestamp')
        
        timeline_data = []
        for entry in history:
            timeline_data.append({
                'timestamp': entry.timestamp.isoformat(),
                'action': entry.action,
                'changed_by': entry.actor.get_full_name() if entry.actor else 'System',
                'previous_status': entry.previous_status,
                'new_status': entry.new_status,
                'reason': entry.change_reason or '',
                'metadata': entry.metadata
            })
        
        # Add current assignment data
        assignment_data = {
            'id': str(assignment.assignment_id),
            'user': {
                'id': assignment.user.pk,
                'name': assignment.user.get_full_name(),
                'email': assignment.user.email
            },
            'shift': {
                'name': assignment.shift.template.name if assignment.shift.template else 'Unknown',
                'start_datetime': assignment.shift.start_datetime.isoformat(),
                'end_datetime': assignment.shift.end_datetime.isoformat(),
            },
            'status': assignment.status,
            'assignment_type': assignment.assignment_type,
            'assigned_at': assignment.assigned_at.isoformat(),
            'assignment_notes': assignment.assignment_notes or ''
        }
        
        return Response({
            'assignment': assignment_data,
            'timeline': timeline_data
        })
        
    except Assignment.DoesNotExist:
        return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assignments_bulk_data(request):
    """
    Get data for bulk operations
    """
    user = request.user
    
    # Get accessible teams
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    # Get available users for assignment
    available_users = User.objects.filter(
        is_active=True,
        team_memberships__team__in=user_teams
    ).distinct()
    
    users_data = []
    for user_obj in available_users:
        users_data.append({
            'id': user_obj.pk,
            'name': user_obj.get_full_name(),
            'email': user_obj.email,
            'teams': [membership.team.name for membership in TeamMembership.objects.filter(user=user_obj, is_active=True)]
        })
    
    # Get available shift templates/types
    from apps.scheduling.models import ShiftTemplate
    shift_templates = ShiftTemplate.objects.filter(is_active=True)
    
    templates_data = []
    for template in shift_templates:
        templates_data.append({
            'id': template.pk,
            'name': template.name,
            'category': template.category.name if template.category else 'General',
            'duration_hours': template.duration_hours,
            'required_skills': [skill.name for skill in template.required_skills.all()] if hasattr(template, 'required_skills') else []
        })
    
    return Response({
        'available_users': users_data,
        'shift_templates': templates_data,
        'assignment_types': Assignment.ASSIGNMENT_TYPES,
        'status_choices': Assignment.STATUS_CHOICES
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assignments_bulk_update(request):
    """
    Perform bulk updates on assignments
    """
    user = request.user
    assignment_ids = request.data.get('assignment_ids', [])
    action = request.data.get('action')
    new_status = request.data.get('new_status')
    new_user_id = request.data.get('new_user_id')
    reason = request.data.get('reason', '')
    
    if not assignment_ids or not action:
        return Response({'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get assignments
    assignments = Assignment.objects.filter(assignment_id__in=assignment_ids)
    
    # Check permissions
    user_teams = Team.objects.filter(
        Q(memberships__user=user) | Q(team_leader=user)
    ).distinct()
    
    assignments = assignments.filter(
        shift__planning_period__teams__in=user_teams
    ).distinct()
    
    updated_count = 0
    errors = []
    
    for assignment in assignments:
        try:
            old_values = {}
            new_values = {}
            
            if action == 'change_status' and new_status:
                old_values['status'] = assignment.status
                assignment.status = new_status
                new_values['status'] = new_status
                
            elif action == 'reassign' and new_user_id:
                new_user = User.objects.get(pk=new_user_id)
                old_values['user'] = assignment.user.get_full_name()
                assignment.user = new_user
                new_values['user'] = new_user.get_full_name()
                
            assignment.save()
            
            # Create history entry
            AssignmentHistory.objects.create(
                assignment=assignment,
                action=f'BULK_{action.upper()}',
                previous_status=old_values.get('status', ''),
                new_status=new_values.get('status', ''),
                change_reason=reason,
                actor=user,
                metadata={'bulk_operation': True, 'old_values': old_values, 'new_values': new_values}
            )
            
            updated_count += 1
            
        except Exception as e:
            errors.append(f'Assignment {assignment.assignment_id}: {str(e)}')
    
    return Response({
        'success': True,
        'updated_count': updated_count,
        'total_requested': len(assignment_ids),
        'errors': errors
    })
