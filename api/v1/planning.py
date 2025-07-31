"""
TPS V1.4 - Planning API Views
Django REST Framework views for planning generation and management
"""

from rest_framework import views, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from api.permissions import PlannerPermission, TacticalPermission, TPSPermission
from api.serializers.assignment_serializers import (
    PlanningRequestSerializer, PlanningResultSerializer, PlanningPeriodSerializer
)
from apps.scheduling.models import PlanningPeriod
from apps.teams.models import Team
from core.services.planning_orchestrator import PlanningOrchestrator
from core.services.data_structures import PlanningResult, ValidationResult

User = get_user_model()


class PlanningAPIView(views.APIView):
    """
    Main planning API for generating and managing planning periods
    """
    permission_classes = [permissions.IsAuthenticated, PlannerPermission]
    
    def post(self, request):
        """
        Generate planning for a team and period
        POST /api/v1/planning/
        """
        serializer = PlanningRequestSerializer(data=request.data)
        if serializer.is_valid():
            team_id = serializer.validated_data['team_id']
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']
            algorithm = serializer.validated_data['algorithm']
            preview_only = serializer.validated_data['preview_only']
            configuration = serializer.validated_data.get('configuration', {})
            
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response(
                    {'error': 'Team not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Initialize planning orchestrator
            orchestrator = PlanningOrchestrator(team)
            
            # Validate prerequisites
            validation_result = orchestrator.validate_prerequisites(start_date, end_date)
            if not validation_result.is_valid:
                return Response({
                    'error': 'Planning prerequisites not met',
                    'validation_errors': validation_result.errors,
                    'warnings': validation_result.warnings
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                if preview_only:
                    # Generate preview without saving
                    result = orchestrator.preview_planning(
                        start_date, end_date, algorithm, configuration
                    )
                    planning_period_id = None
                else:
                    # Generate and save planning
                    result = orchestrator.generate_complete_planning(
                        start_date, end_date, algorithm, configuration,
                        created_by=request.user
                    )
                    planning_period_id = result.planning_period_id if hasattr(result, 'planning_period_id') else None
                
                # Serialize result
                result_data = {
                    'planning_period_id': planning_period_id,
                    'success': result.success,
                    'total_shifts': len(result.shift_assignments),
                    'assigned_shifts': len([a for a in result.shift_assignments if a.status == 'CONFIRMED']),
                    'unassigned_shifts': len([a for a in result.shift_assignments if a.status == 'UNASSIGNED']),
                    'coverage_percentage': result.coverage_percentage,
                    'fairness_score': result.fairness_score,
                    'conflicts': result.conflicts,
                    'warnings': result.warnings,
                    'recommendations': result.recommendations
                }
                
                if preview_only:
                    # Include assignment details for preview
                    from api.serializers.assignment_serializers import AssignmentListSerializer
                    assignments_data = []
                    for assignment in result.shift_assignments:
                        assignments_data.append({
                            'shift_id': assignment.shift.id if hasattr(assignment, 'shift') else None,
                            'user_id': assignment.user.id if hasattr(assignment, 'user') else None,
                            'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip() if hasattr(assignment, 'user') else None,
                            'role': assignment.role if hasattr(assignment, 'role') else 'primary',
                            'status': assignment.status,
                            'shift_date': assignment.shift.date if hasattr(assignment, 'shift') else None,
                            'shift_name': assignment.shift.template.name if hasattr(assignment, 'shift') and hasattr(assignment.shift, 'template') else None
                        })
                    result_data['assignments'] = assignments_data
                
                response_serializer = PlanningResultSerializer(result_data)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Planning generation failed: {str(e)}',
                    'success': False
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """
        Get planning status and history
        GET /api/v1/planning/?team_id=123
        """
        team_id = request.query_params.get('team_id')
        if not team_id:
            return Response(
                {'error': 'team_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                {'error': 'Team not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get recent planning periods
        planning_periods = PlanningPeriod.objects.filter(
            team=team
        ).order_by('-created_at')[:10]
        
        serializer = PlanningPeriodSerializer(planning_periods, many=True)
        return Response({
            'team_id': team_id,
            'team_name': team.name,
            'planning_periods': serializer.data
        })
    
    def put(self, request):
        """
        Update existing planning period
        PUT /api/v1/planning/
        """
        planning_period_id = request.data.get('planning_period_id')
        if not planning_period_id:
            return Response(
                {'error': 'planning_period_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            planning_period = PlanningPeriod.objects.get(id=planning_period_id)
        except PlanningPeriod.DoesNotExist:
            return Response(
                {'error': 'Planning period not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update planning period with new data
        update_data = request.data.copy()
        update_data.pop('planning_period_id', None)
        
        serializer = PlanningPeriodSerializer(planning_period, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """
        Cancel/delete planning period
        DELETE /api/v1/planning/?planning_period_id=123
        """
        planning_period_id = request.query_params.get('planning_period_id')
        if not planning_period_id:
            return Response(
                {'error': 'planning_period_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            planning_period = PlanningPeriod.objects.get(id=planning_period_id)
        except PlanningPeriod.DoesNotExist:
            return Response(
                {'error': 'Planning period not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if planning can be cancelled
        if planning_period.status == 'APPLIED':
            return Response(
                {'error': 'Cannot delete applied planning period'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status instead of deleting
        planning_period.status = 'CANCELLED'
        planning_period.save()
        
        return Response({'message': 'Planning period cancelled successfully'})


class PlanningPreviewAPIView(views.APIView):
    """
    API for previewing planning without saving
    """
    permission_classes = [permissions.IsAuthenticated, TacticalPermission]
    
    def post(self, request):
        """
        Preview planning without saving to database
        POST /api/v1/planning/preview/
        """
        # Use the same logic as PlanningAPIView but force preview_only=True
        data = request.data.copy()
        data['preview_only'] = True
        
        # Create new request with modified data
        from django.http import QueryDict
        modified_request = type('Request', (), {})()
        modified_request.data = data
        modified_request.user = request.user
        
        # Delegate to main planning API
        planning_api = PlanningAPIView()
        planning_api.request = modified_request
        return planning_api.post(modified_request)


class PlanningStatusAPIView(views.APIView):
    """
    API for checking planning generation status
    """
    permission_classes = [permissions.IsAuthenticated, TPSPermission]
    
    def get(self, request, planning_period_id):
        """
        Get status of specific planning period
        GET /api/v1/planning/{id}/status/
        """
        try:
            planning_period = PlanningPeriod.objects.get(id=planning_period_id)
        except PlanningPeriod.DoesNotExist:
            return Response(
                {'error': 'Planning period not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get assignment statistics
        from apps.assignments.models import Assignment
        assignments = Assignment.objects.filter(
            shift__date__range=[planning_period.start_date, planning_period.end_date],
            shift__team=planning_period.team
        )
        
        total_assignments = assignments.count()
        confirmed_assignments = assignments.filter(status='CONFIRMED').count()
        pending_assignments = assignments.filter(status='PROPOSED').count()
        coverage_percentage = (confirmed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        return Response({
            'planning_period_id': planning_period.id,
            'status': planning_period.status,
            'team_name': planning_period.team.name,
            'start_date': planning_period.start_date,
            'end_date': planning_period.end_date,
            'algorithm_used': planning_period.algorithm_used,
            'created_at': planning_period.created_at,
            'applied_at': planning_period.applied_at,
            'statistics': {
                'total_assignments': total_assignments,
                'confirmed_assignments': confirmed_assignments,
                'pending_assignments': pending_assignments,
                'coverage_percentage': round(coverage_percentage, 2)
            },
            'results': planning_period.results
        })


class PlanningValidationAPIView(views.APIView):
    """
    API for validating planning prerequisites
    """
    permission_classes = [permissions.IsAuthenticated, TacticalPermission]
    
    def post(self, request):
        """
        Validate planning prerequisites for a team and period
        POST /api/v1/planning/validate/
        """
        team_id = request.data.get('team_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([team_id, start_date, end_date]):
            return Response(
                {'error': 'team_id, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            team = Team.objects.get(id=team_id)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (Team.DoesNotExist, ValueError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize orchestrator and validate
        orchestrator = PlanningOrchestrator(team)
        validation_result = orchestrator.validate_prerequisites(start_date, end_date)
        
        return Response({
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'team_id': team_id,
            'team_name': team.name,
            'start_date': start_date,
            'end_date': end_date,
            'validation_details': {
                'team_members_count': team.memberships.filter(is_active=True).count(),
                'min_required_members': team.min_members_per_shift,
                'period_duration_days': (end_date - start_date).days,
                'max_allowed_days': 84  # 12 weeks
            }
        })


class PlanningApplyAPIView(views.APIView):
    """
    API for applying planning periods (making assignments official)
    """
    permission_classes = [permissions.IsAuthenticated, PlannerPermission]
    
    def post(self, request, planning_period_id):
        """
        Apply a planning period (make all assignments official)
        POST /api/v1/planning/{id}/apply/
        """
        try:
            planning_period = PlanningPeriod.objects.get(id=planning_period_id)
        except PlanningPeriod.DoesNotExist:
            return Response(
                {'error': 'Planning period not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if planning_period.status != 'COMPLETED':
            return Response(
                {'error': 'Planning period must be completed before applying'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply the planning
        try:
            orchestrator = PlanningOrchestrator(planning_period.team)
            result = orchestrator.apply_planning_period(planning_period, applied_by=request.user)
            
            if result.success:
                return Response({
                    'message': 'Planning applied successfully',
                    'planning_period_id': planning_period.id,
                    'applied_assignments': result.applied_assignments,
                    'applied_at': planning_period.applied_at
                })
            else:
                return Response({
                    'error': 'Failed to apply planning',
                    'errors': result.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': f'Planning application failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
