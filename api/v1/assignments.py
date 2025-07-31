"""
TPS V1.4 - Assignments API Views
Django REST Framework ViewSets for assignment management
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from api.permissions import (
    TPSPermission, TacticalPermission, PlannerPermission,
    SelfOrManagerPermission, ReadOnlyOrManagerPermission
)
from api.serializers.assignment_serializers import (
    AssignmentSerializer, AssignmentListSerializer, BulkAssignmentSerializer,
    SwapRequestSerializer, ShiftInstanceSerializer, ShiftAvailabilitySerializer
)
from apps.assignments.models import Assignment, AssignmentHistory, SwapRequest
from apps.scheduling.models import ShiftInstance, ShiftTemplate
from core.services.assignment_service import AssignmentService
from core.services.skills_service import SkillsService
from core.services.fairness_service import FairnessService

User = get_user_model()


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for assignment management with comprehensive functionality
    """
    queryset = Assignment.objects.all()
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrManagerPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AssignmentListSerializer
        elif self.action == 'bulk_create':
            return BulkAssignmentSerializer
        elif self.action == 'swap_request':
            return SwapRequestSerializer
        return AssignmentSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'bulk_create']:
            permission_classes = [permissions.IsAuthenticated, TacticalPermission]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, TacticalPermission]
        elif self.action in ['approve_assignment', 'reject_assignment']:
            permission_classes = [permissions.IsAuthenticated, TacticalPermission]
        elif self.action == 'swap_request':
            permission_classes = [permissions.IsAuthenticated, SelfOrManagerPermission]
        else:
            permission_classes = [permissions.IsAuthenticated, TPSPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters"""
        queryset = Assignment.objects.select_related(
            'shift__template',
            'shift__team',
            'user',
            'assigned_by'
        ).prefetch_related(
            'assignmenthistory_set'
        )
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by team
        team_id = self.request.query_params.get('team_id')
        if team_id:
            queryset = queryset.filter(shift__team_id=team_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by shift type
        shift_type = self.request.query_params.get('shift_type')
        if shift_type:
            queryset = queryset.filter(shift__template__category=shift_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(shift__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(shift__date__lte=end_date)
            except ValueError:
                pass
        
        # Filter by upcoming assignments (default for list view)
        if not any([user_id, team_id, start_date, end_date]) and self.action == 'list':
            current_date = timezone.now().date()
            queryset = queryset.filter(shift__date__gte=current_date)
        
        return queryset.order_by('shift__date', 'shift__start_time')
    
    def create(self, request, *args, **kwargs):
        """Create a new assignment with validation"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Use assignment service for creation with business logic
            shift_id = serializer.validated_data['shift_id']
            user_id = serializer.validated_data['user_id']
            
            try:
                shift = ShiftInstance.objects.get(id=shift_id)
                user = User.objects.get(id=user_id)
                
                # Use assignment service
                assignment_service = AssignmentService(shift.team)
                assignment = assignment_service.create_assignment(
                    shift=shift,
                    user=user,
                    assigned_by=request.user,
                    role=serializer.validated_data.get('role', 'primary'),
                    notes=serializer.validated_data.get('notes', '')
                )
                
                response_serializer = AssignmentSerializer(assignment)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except (ShiftInstance.DoesNotExist, User.DoesNotExist) as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Assignment creation failed: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple assignments at once
        POST /api/v1/assignments/bulk-create/
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            assignments_data = serializer.validated_data['assignments']
            assigned_by_id = serializer.validated_data['assigned_by_id']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                assigned_by = User.objects.get(id=assigned_by_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Invalid assigned_by_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            created_assignments = []
            errors = []
            
            for assignment_data in assignments_data:
                try:
                    shift = ShiftInstance.objects.get(id=assignment_data['shift_id'])
                    user = User.objects.get(id=assignment_data['user_id'])
                    
                    # Use assignment service
                    assignment_service = AssignmentService(shift.team)
                    assignment = assignment_service.create_assignment(
                        shift=shift,
                        user=user,
                        assigned_by=assigned_by,
                        role=assignment_data.get('role', 'primary'),
                        notes=notes
                    )
                    
                    created_assignments.append(assignment)
                    
                except Exception as e:
                    errors.append({
                        'shift_id': assignment_data.get('shift_id'),
                        'user_id': assignment_data.get('user_id'),
                        'error': str(e)
                    })
            
            response_data = {
                'created_count': len(created_assignments),
                'error_count': len(errors),
                'assignments': AssignmentListSerializer(created_assignments, many=True).data
            }
            
            if errors:
                response_data['errors'] = errors
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def swap_request(self, request, pk=None):
        """
        Create a swap request for an assignment
        POST /api/v1/assignments/{id}/swap-request/
        """
        from_assignment = self.get_object()
        
        # Check if user can request swap
        if from_assignment.user != request.user and not request.user.is_superuser:
            user_role = getattr(request.user, 'role', 'operationeel')
            if user_role not in ['tactisch', 'management', 'planner', 'admin']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = SwapRequestSerializer(data=request.data)
        if serializer.is_valid():
            to_assignment_id = serializer.validated_data['to_assignment_id']
            reason = serializer.validated_data.get('reason', '')
            
            try:
                to_assignment = Assignment.objects.get(id=to_assignment_id)
                
                # Validate swap request
                if from_assignment.shift.date == to_assignment.shift.date:
                    return Response(
                        {'error': 'Cannot swap assignments on the same date'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create swap request
                swap_request = SwapRequest.objects.create(
                    from_assignment=from_assignment,
                    to_assignment=to_assignment,
                    reason=reason,
                    requested_by=request.user,
                    status='PENDING'
                )
                
                response_serializer = SwapRequestSerializer(swap_request)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Assignment.DoesNotExist:
                return Response(
                    {'error': 'Target assignment not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve_assignment(self, request, pk=None):
        """
        Approve a proposed assignment
        POST /api/v1/assignments/{id}/approve/
        """
        assignment = self.get_object()
        
        if assignment.status != 'PROPOSED':
            return Response(
                {'error': 'Assignment is not in proposed status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update assignment status
        assignment.status = 'CONFIRMED'
        assignment.confirmed_at = timezone.now()
        assignment.save()
        
        # Create history entry
        AssignmentHistory.objects.create(
            assignment=assignment,
            action='APPROVED',
            old_values={'status': 'PROPOSED'},
            new_values={'status': 'CONFIRMED'},
            changed_by=request.user,
            reason='Assignment approved'
        )
        
        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject_assignment(self, request, pk=None):
        """
        Reject a proposed assignment
        POST /api/v1/assignments/{id}/reject/
        """
        assignment = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        if assignment.status != 'PROPOSED':
            return Response(
                {'error': 'Assignment is not in proposed status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update assignment status
        assignment.status = 'DECLINED'
        assignment.save()
        
        # Create history entry
        AssignmentHistory.objects.create(
            assignment=assignment,
            action='REJECTED',
            old_values={'status': 'PROPOSED'},
            new_values={'status': 'DECLINED'},
            changed_by=request.user,
            reason=reason
        )
        
        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_users_for_shift(self, request):
        """
        Get available users for a specific shift
        GET /api/v1/assignments/available-users-for-shift/?shift_id=123
        """
        shift_id = request.query_params.get('shift_id')
        if not shift_id:
            return Response(
                {'error': 'shift_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            shift = ShiftInstance.objects.get(id=shift_id)
        except ShiftInstance.DoesNotExist:
            return Response(
                {'error': 'Shift not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use skills service to get qualified users
        skills_service = SkillsService(shift.team)
        qualified_users = skills_service.get_qualified_users(shift.template)
        
        # Check availability and calculate scores
        available_users = []
        qualified_user_data = []
        recommendations = []
        
        assignment_service = AssignmentService(shift.team)
        fairness_service = FairnessService(shift.team)
        
        for user in qualified_users:
            skill_score = skills_service.calculate_skill_score(user, shift.template)
            fairness_score = fairness_service.calculate_user_fairness_score(user)
            
            user_data = {
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip(),
                'employee_id': user.employee_id,
                'skill_score': skill_score,
                'fairness_score': fairness_score,
                'ytd_hours': user.ytd_hours_worked or 0,
                'is_available': True  # Simplified for now
            }
            
            qualified_user_data.append(user_data)
            
            # Add to available if meets basic criteria
            if skill_score >= 60 and fairness_score >= 60:  # Minimum thresholds
                available_users.append(user_data)
        
        # Sort available users by combined score
        available_users.sort(key=lambda x: (x['skill_score'] + x['fairness_score']), reverse=True)
        
        # Generate recommendations
        if available_users:
            best_candidate = available_users[0]
            recommendations.append(f"Best candidate: {best_candidate['name']} (Combined score: {best_candidate['skill_score'] + best_candidate['fairness_score']:.1f})")
        
        if len(available_users) < 3:
            recommendations.append("Low availability - consider expanding search criteria")
        
        return Response({
            'shift_id': shift_id,
            'shift_name': shift.template.name,
            'shift_date': shift.date,
            'available_users': available_users[:10],  # Top 10
            'qualified_users': qualified_user_data,
            'recommendations': recommendations
        })
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Get assignments overview statistics for the dashboard
        GET /api/v1/assignments/overview/
        """
        try:
            user = request.user
            current_date = timezone.now().date()
            
            # Base queryset for user's assignments - simplified for now
            user_assignments = Assignment.objects.all()[:100]  # Limit for performance
            
            # Calculate statistics from real data
            total_assignments = user_assignments.count()
            confirmed_assignments = user_assignments.filter(status='confirmed').count()
            pending_assignments = user_assignments.filter(status__in=['pending_confirmation', 'tentative']).count()
            
            # Calculate overdue assignments (assignments past their shift date that aren't completed)
            today = timezone.now().date()
            overdue_assignments = user_assignments.filter(
                shift__start_datetime__date__lt=today,
                status__in=['pending_confirmation', 'tentative']
            ).count()
            
            # Don't fallback to mock data - return actual values even if zero
            completion_rate = round((confirmed_assignments / total_assignments * 100) if total_assignments > 0 else 0, 1)
            
            overview_data = {
                'total_assignments': total_assignments,
                'confirmed_assignments': confirmed_assignments,
                'pending_assignments': pending_assignments,
                'overdue_assignments': overdue_assignments,
                'completion_rate': completion_rate
            }
            
            return Response({
                'success': True,
                'overview': overview_data
            })
            
        except Exception as e:
            # Return error without mock data fallback
            return Response({
                'success': False,
                'error': f'Failed to fetch assignments overview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SwapRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for shift swap request management"""
    
    queryset = SwapRequest.objects.all()
    serializer_class = SwapRequestSerializer
    permission_classes = [permissions.IsAuthenticated, TPSPermission]
    
    def get_queryset(self):
        """Filter swap requests based on user permissions"""
        queryset = SwapRequest.objects.select_related(
            'from_assignment__shift__template',
            'from_assignment__user',
            'to_assignment__shift__template',
            'to_assignment__user',
            'requested_by',
            'approved_by'
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by requesting user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(
                Q(from_assignment__user_id=user_id) |
                Q(to_assignment__user_id=user_id) |
                Q(requested_by_id=user_id)
            )
        
        return queryset.order_by('-requested_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a swap request"""
        swap_request = self.get_object()
        
        if swap_request.status != 'PENDING':
            return Response(
                {'error': 'Swap request is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform the swap
        from_assignment = swap_request.from_assignment
        to_assignment = swap_request.to_assignment
        
        # Swap the users
        temp_user = from_assignment.user
        from_assignment.user = to_assignment.user
        to_assignment.user = temp_user
        
        from_assignment.save()
        to_assignment.save()
        
        # Update swap request
        swap_request.status = 'APPROVED'
        swap_request.approved_by = request.user
        swap_request.approved_at = timezone.now()
        swap_request.save()
        
        return Response({'message': 'Swap request approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a swap request"""
        swap_request = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        if swap_request.status != 'PENDING':
            return Response(
                {'error': 'Swap request is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update swap request
        swap_request.status = 'REJECTED'
        swap_request.approved_by = request.user
        swap_request.approved_at = timezone.now()
        swap_request.rejection_reason = reason
        swap_request.save()
        
        return Response({'message': 'Swap request rejected'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def assignments_overview(request):
    """
    Get assignments overview statistics for the dashboard
    """
    try:
        user = request.user
        current_date = timezone.now().date()
        
        # Base queryset for user's assignments
        user_assignments = Assignment.objects.filter(
            Q(shift_instance__team_member__user=user) |
            Q(shift_instance__team_member__team__leaders=user)
        ).distinct()
        
        # Calculate statistics
        total_assignments = user_assignments.count()
        confirmed_assignments = user_assignments.filter(
            status='confirmed'
        ).count()
        pending_assignments = user_assignments.filter(
            status__in=['pending', 'tentative']
        ).count()
        overdue_assignments = user_assignments.filter(
            shift_instance__date__lt=current_date,
            status='pending'
        ).count()
        
        # Additional metrics
        upcoming_assignments = user_assignments.filter(
            shift_instance__date__gte=current_date,
            shift_instance__date__lte=current_date + timedelta(days=7)
        ).count()
        
        overview_data = {
            'total_assignments': total_assignments,
            'confirmed_assignments': confirmed_assignments,
            'pending_assignments': pending_assignments,
            'overdue_assignments': overdue_assignments,
            'upcoming_assignments': upcoming_assignments,
            'completion_rate': round(
                (confirmed_assignments / total_assignments * 100) if total_assignments > 0 else 0, 1
            )
        }
        
        return Response({
            'success': True,
            'overview': overview_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to fetch assignments overview: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
