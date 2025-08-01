"""
Simple API endpoints for testing shift swap functionality
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

from apps.assignments.models import Assignment, SwapRequest


@login_required
def simple_assignments_list(request):
    """Simple assignments list endpoint"""
    try:
        assignments = Assignment.objects.filter(user=request.user).select_related(
            'shift__template', 'user'
        )
        
        results = []
        for assignment in assignments:
            results.append({
                'id': assignment.id,
                'shift_name': assignment.shift.template.name,
                'shift_date': assignment.shift.date.isoformat(),
                'start_time': assignment.shift.start_datetime.strftime('%H:%M'),
                'end_time': assignment.shift.end_datetime.strftime('%H:%M'),
                'status': assignment.status,
                'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip()
            })
        
        return JsonResponse({
            'success': True,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required  
def simple_swap_requests_list(request):
    """Simple swap requests list endpoint"""
    try:
        swap_requests = SwapRequest.objects.filter(
            requesting_user=request.user
        ).select_related(
            'requesting_assignment__shift__template',
            'requesting_assignment__user',
            'target_assignment__shift__template',
            'target_assignment__user'
        )
        
        results = []
        for swap_request in swap_requests:
            results.append({
                'id': swap_request.id,
                'status': swap_request.status,
                'urgency_level': swap_request.urgency_level,
                'reason': swap_request.reason,
                'requested_at': swap_request.requested_at.isoformat(),
                'expires_at': swap_request.expires_at.isoformat() if swap_request.expires_at else None,
                'requesting_assignment': {
                    'shift_name': swap_request.requesting_assignment.shift.template.name,
                    'shift_date': swap_request.requesting_assignment.shift.date.isoformat(),
                    'start_time': swap_request.requesting_assignment.shift.start_datetime.strftime('%H:%M'),
                    'end_time': swap_request.requesting_assignment.shift.end_datetime.strftime('%H:%M'),
                },
                'target_assignment': {
                    'shift_name': swap_request.target_assignment.shift.template.name,
                    'shift_date': swap_request.target_assignment.shift.date.isoformat(),
                    'start_time': swap_request.target_assignment.shift.start_datetime.strftime('%H:%M'),
                    'end_time': swap_request.target_assignment.shift.end_datetime.strftime('%H:%M'),
                } if swap_request.target_assignment else None
            })
        
        return JsonResponse({
            'success': True,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SimpleSwapRequestCreate(View):
    """Simple swap request creation endpoint"""
    
    @method_decorator(login_required)
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Get the requesting assignment
            requesting_assignment = Assignment.objects.get(
                id=data['requesting_assignment_id'],
                user=request.user  # Ensure user owns this assignment
            )
            
            # Get target assignment if it's a direct swap
            target_assignment = None
            if data.get('target_assignment_id'):
                target_assignment = Assignment.objects.get(
                    id=data['target_assignment_id']
                )
            
            # Create the swap request
            swap_request = SwapRequest.objects.create(
                requesting_user=request.user,
                requesting_assignment=requesting_assignment,
                target_assignment=target_assignment,
                target_user=target_assignment.user if target_assignment else None,
                swap_type=data['swap_type'],
                reason=data['reason'],
                urgency_level=data['urgency_level'],
                additional_notes=data.get('additional_notes', ''),
                expires_at=data.get('expires_at')
            )
            
            return JsonResponse({
                'success': True,
                'swap_request_id': swap_request.id,
                'message': 'Swap request created successfully'
            })
            
        except Assignment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Assignment not found or not owned by user'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@login_required
def simple_available_assignments(request):
    """Simple available assignments for swapping"""
    try:
        # Get assignments from other users that are available for swapping
        assignments = Assignment.objects.exclude(
            user=request.user
        ).filter(
            status__in=['confirmed', 'pending_confirmation'],
            shift__date__gte=request.user.date_joined.date()  # Simple future date check
        ).select_related('shift__template', 'user')[:20]  # Limit for performance
        
        results = []
        for assignment in assignments:
            results.append({
                'id': assignment.id,
                'shift_name': assignment.shift.template.name,
                'shift_date': assignment.shift.date.isoformat(),
                'start_time': assignment.shift.start_datetime.strftime('%H:%M'),
                'end_time': assignment.shift.end_datetime.strftime('%H:%M'),
                'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip()
            })
        
        return JsonResponse({
            'success': True,
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)