"""
Assignment Operations API for TPS V1.4
Provides CRUD operations for assignments including drag & drop moves
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from apps.assignments.models import Assignment
from apps.accounts.models import User
from apps.scheduling.models import ShiftInstance


@api_view(['POST'])
@permission_classes([AllowAny])  # Temporarily allow unauthenticated access for development
def move_assignment(request, assignment_id):
    """
    Move an assignment to a different user and/or date
    """
    try:
        # Get the assignment
        try:
            assignment = Assignment.objects.get(pk=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get parameters
        target_user_id = request.data.get('user_id')
        target_date = request.data.get('date')
        
        if not target_user_id or not target_date:
            return Response({
                'error': 'Both user_id and date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target user
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return Response({'error': 'Target user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse target date
        try:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use transaction to ensure data consistency
        with transaction.atomic():
            # Get the original shift details
            original_shift = assignment.shift
            
            # Check if we need to create a new shift or use existing one
            target_shift = None
            
            # If moving to different date, we need a new shift
            if original_shift.date != target_date_obj:
                # Create new shift instance for target date
                target_start = datetime.combine(
                    target_date_obj, 
                    original_shift.start_datetime.time()
                )
                target_end = datetime.combine(
                    target_date_obj, 
                    original_shift.end_datetime.time()
                )
                
                # Make timezone aware
                target_start = timezone.make_aware(target_start)
                target_end = timezone.make_aware(target_end)
                
                target_shift = ShiftInstance.objects.create(
                    template=original_shift.template,
                    date=target_date_obj,
                    start_datetime=target_start,
                    end_datetime=target_end,
                    required_skills=original_shift.required_skills,
                    max_assignments=original_shift.max_assignments
                )
            else:
                target_shift = original_shift
            
            # Update the assignment
            assignment.user = target_user
            assignment.shift = target_shift
            assignment.assigned_at = timezone.now()
            assignment.save()
            
            # If we created a new shift and the old one has no more assignments, clean it up
            if target_shift != original_shift:
                remaining_assignments = Assignment.objects.filter(shift=original_shift).count()
                if remaining_assignments == 0:
                    original_shift.delete()
        
        return Response({
            'success': True,
            'message': 'Assignment moved successfully',
            'assignment': {
                'id': assignment.pk,
                'user_id': assignment.user.pk,
                'user_name': assignment.user.get_full_name(),
                'date': assignment.shift.date.isoformat(),
                'start_time': assignment.shift.start_datetime.strftime('%H:%M'),
                'end_time': assignment.shift.end_datetime.strftime('%H:%M'),
                'type': assignment.shift.template.category.name if assignment.shift.template.category else 'Unknown'
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to move assignment: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def copy_assignment(request, assignment_id):
    """
    Copy an assignment to a different user and/or date
    """
    try:
        # Get the assignment
        try:
            assignment = Assignment.objects.get(pk=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get parameters
        target_user_id = request.data.get('user_id')
        target_date = request.data.get('date')
        
        if not target_user_id or not target_date:
            return Response({
                'error': 'Both user_id and date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target user
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return Response({'error': 'Target user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse target date
        try:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            original_shift = assignment.shift
            
            # Create new shift for target date if needed
            if original_shift.date != target_date_obj:
                target_start = datetime.combine(
                    target_date_obj, 
                    original_shift.start_datetime.time()
                )
                target_end = datetime.combine(
                    target_date_obj, 
                    original_shift.end_datetime.time()
                )
                
                target_start = timezone.make_aware(target_start)
                target_end = timezone.make_aware(target_end)
                
                target_shift = ShiftInstance.objects.create(
                    template=original_shift.template,
                    date=target_date_obj,
                    start_datetime=target_start,
                    end_datetime=target_end,
                    required_skills=original_shift.required_skills,
                    max_assignments=original_shift.max_assignments
                )
            else:
                target_shift = original_shift
            
            # Create new assignment (copy)
            new_assignment = Assignment.objects.create(
                user=target_user,
                shift=target_shift,
                status=assignment.status,
                assigned_at=timezone.now()
            )
        
        return Response({
            'success': True,
            'message': 'Assignment copied successfully',
            'assignment': {
                'id': new_assignment.pk,
                'user_id': new_assignment.user.pk,
                'user_name': new_assignment.user.get_full_name(),
                'date': new_assignment.shift.date.isoformat(),
                'start_time': new_assignment.shift.start_datetime.strftime('%H:%M'),
                'end_time': new_assignment.shift.end_datetime.strftime('%H:%M'),
                'type': new_assignment.shift.template.category.name if new_assignment.shift.template.category else 'Unknown'
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to copy assignment: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_assignment(request, assignment_id):
    """
    Delete an assignment
    """
    try:
        # Get the assignment
        try:
            assignment = Assignment.objects.get(pk=assignment_id)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        with transaction.atomic():
            shift = assignment.shift
            assignment.delete()
            
            # If shift has no more assignments, consider deleting it
            remaining_assignments = Assignment.objects.filter(shift=shift).count()
            if remaining_assignments == 0:
                shift.delete()
        
        return Response({
            'success': True,
            'message': 'Assignment deleted successfully'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to delete assignment: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_move_assignments(request):
    """
    Move multiple assignments to the same target
    """
    try:
        assignment_ids = request.data.get('assignment_ids', [])
        target_user_id = request.data.get('user_id')
        target_date = request.data.get('date')
        
        if not assignment_ids or not target_user_id or not target_date:
            return Response({
                'error': 'assignment_ids, user_id and date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target user
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return Response({'error': 'Target user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse target date
        try:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
        
        moved_assignments = []
        failed_assignments = []
        
        with transaction.atomic():
            for assignment_id in assignment_ids:
                try:
                    assignment = Assignment.objects.get(pk=assignment_id)
                    
                    # Similar logic to single move
                    original_shift = assignment.shift
                    
                    if original_shift.date != target_date_obj:
                        target_start = datetime.combine(
                            target_date_obj, 
                            original_shift.start_datetime.time()
                        )
                        target_end = datetime.combine(
                            target_date_obj, 
                            original_shift.end_datetime.time()
                        )
                        
                        target_start = timezone.make_aware(target_start)
                        target_end = timezone.make_aware(target_end)
                        
                        target_shift, created = ShiftInstance.objects.get_or_create(
                            template=original_shift.template,
                            date=target_date_obj,
                            defaults={
                                'start_datetime': target_start,
                                'end_datetime': target_end,
                                'required_skills': original_shift.required_skills,
                                'max_assignments': original_shift.max_assignments
                            }
                        )
                    else:
                        target_shift = original_shift
                    
                    assignment.user = target_user
                    assignment.shift = target_shift
                    assignment.assigned_at = timezone.now()
                    assignment.save()
                    
                    moved_assignments.append(assignment_id)
                    
                except Assignment.DoesNotExist:
                    failed_assignments.append({'id': assignment_id, 'error': 'Assignment not found'})
                except Exception as e:
                    failed_assignments.append({'id': assignment_id, 'error': str(e)})
        
        return Response({
            'success': True,
            'message': f'Moved {len(moved_assignments)} assignments successfully',
            'moved_assignments': moved_assignments,
            'failed_assignments': failed_assignments
        })
        
    except Exception as e:
        return Response(
            {'error': f'Bulk move failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
