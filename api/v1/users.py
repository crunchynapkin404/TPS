"""
TPS V1.4 - User API Views
Django REST Framework ViewSets for user management
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta

from api.permissions import (
    TPSPermission, SelfOrManagerPermission, TacticalPermission,
    ManagementPermission
)
from api.serializers.user_serializers import (
    UserSerializer, UserListSerializer, UserCreateSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, UserScheduleSerializer,
    UserStatisticsSerializer
)
from core.services.fairness_service import FairnessService
from core.services.assignment_service import AssignmentService
from core.services.skills_service import SkillsService

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management with comprehensive functionality
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, TPSPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        elif self.action == 'get_schedule':
            return UserScheduleSerializer
        elif self.action == 'get_workload_stats':
            return UserStatisticsSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, ManagementPermission]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, SelfOrManagerPermission]
        elif self.action in ['get_workload_stats', 'update_availability']:
            permission_classes = [permissions.IsAuthenticated, SelfOrManagerPermission]
        else:
            permission_classes = [permissions.IsAuthenticated, TPSPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters"""
        queryset = User.objects.select_related().prefetch_related(
            'user_skills__skill',
            'team_memberships__team',
            'team_memberships__role'
        )
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by team
        team_id = self.request.query_params.get('team_id')
        if team_id:
            queryset = queryset.filter(
                team_memberships__team_id=team_id,
                team_memberships__is_active=True
            )
        
        # Filter by skills
        skill_ids = self.request.query_params.getlist('skill_ids')
        if skill_ids:
            queryset = queryset.filter(
                user_skills__skill_id__in=skill_ids,
                user_skills__proficiency_level__in=['advanced', 'expert']
            ).distinct()
        
        # Search by name or employee ID
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(username__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def get_schedule(self, request, pk=None):
        """
        Get user's schedule for a date range
        GET /api/v1/users/{id}/schedule/?start_date=2024-01-01&end_date=2024-01-31
        """
        user = self.get_object()
        
        # Parse date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date:
            start_date = timezone.now().date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if not end_date:
            end_date = start_date + timedelta(days=30)
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get assignments for date range
        assignments = user.assignment_set.filter(
            shift__date__range=[start_date, end_date]
        ).select_related(
            'shift__template',
            'shift__team'
        ).order_by('shift__date', 'shift__start_datetime')
        
        schedule_data = []
        for assignment in assignments:
            shift = assignment.shift
            schedule_data.append({
                'date': shift.date,
                'shift_type': shift.template.category,
                'shift_name': shift.template.name,
                'start_datetime': shift.start_datetime,
                'end_datetime': shift.end_datetime,
                'location': getattr(shift, 'location_override', None) or getattr(shift.template, 'location', ''),
                'status': assignment.status,
                'assignment_id': assignment.id
            })
        
        serializer = UserScheduleSerializer(schedule_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def get_workload_stats(self, request, pk=None):
        """
        Get user's workload statistics and fairness scores
        GET /api/v1/users/{id}/workload-stats/
        """
        user = self.get_object()
        fairness_service = FairnessService()
        
        # Calculate YTD statistics
        current_year = timezone.now().year
        stats = {
            'ytd_hours_worked': user.ytd_hours_worked or 0,
            'ytd_weeks_waakdienst': user.ytd_weeks_waakdienst or 0,
            'ytd_weeks_incident': user.ytd_weeks_incident or 0,
            'ytd_assignments_completed': user.assignment_set.filter(
                status='COMPLETED',
                shift__date__year=current_year
            ).count(),
            'ytd_assignments_cancelled': user.assignment_set.filter(
                status='CANCELLED',
                shift__date__year=current_year
            ).count(),
            'average_performance_rating': user.performance_rating or 0,
            'fairness_score': fairness_service.calculate_user_fairness_score(user)
        }
        
        serializer = UserStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_availability(self, request, pk=None):
        """
        Update user's availability preferences
        POST /api/v1/users/{id}/update-availability/
        """
        user = self.get_object()
        
        # Validate availability data
        availability_data = request.data.get('availability_constraints', {})
        
        # Update user's shift preferences
        if not user.shift_preferences:
            user.shift_preferences = {}
        
        user.shift_preferences['availability_constraints'] = availability_data
        user.save(update_fields=['shift_preferences'])
        
        return Response({
            'message': 'Availability preferences updated successfully',
            'availability_constraints': availability_data
        })
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Change user's password
        POST /api/v1/users/{id}/change-password/
        """
        user = self.get_object()
        
        # Check if user can change this password
        if user != request.user and not request.user.is_superuser:
            user_role = getattr(request.user, 'role', 'operationeel')
            if user_role not in ['management', 'admin']:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def available_for_shift(self, request):
        """
        Get users available for a specific shift
        GET /api/v1/users/available-for-shift/?shift_id=123
        """
        shift_id = request.query_params.get('shift_id')
        if not shift_id:
            return Response(
                {'error': 'shift_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.scheduling.models import ShiftInstance
            shift = ShiftInstance.objects.get(id=shift_id)
        except ShiftInstance.DoesNotExist:
            return Response(
                {'error': 'Shift not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use skills service to get qualified users
        skills_service = SkillsService()
        qualified_users = skills_service.get_qualified_users(shift.template)
        
        # Use assignment service to check availability
        assignment_service = AssignmentService()
        available_users = []
        
        for user in qualified_users:
            if assignment_service.is_user_available(user, shift.date, shift.start_time, shift.end_time):
                fairness_service = FairnessService()
                score = fairness_service.calculate_assignment_score(user, shift)
                
                available_users.append({
                    'id': user.id,
                    'name': f"{user.first_name} {user.last_name}".strip(),
                    'employee_id': user.employee_id,
                    'skill_score': skills_service.calculate_skill_score(user, shift.template),
                    'fairness_score': score,
                    'ytd_hours': user.ytd_hours_worked or 0,
                    'last_assignment': assignment_service.get_last_assignment_date(user)
                })
        
        # Sort by combined score (skill + fairness)
        available_users.sort(key=lambda x: (x['skill_score'] + x['fairness_score']), reverse=True)
        
        return Response({
            'shift_id': shift_id,
            'shift_name': shift.template.name,
            'shift_date': shift.date,
            'available_users': available_users
        })
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """
        Get list of all departments
        GET /api/v1/users/departments/
        """
        departments = User.objects.values_list('department', flat=True).distinct()
        departments = [dept for dept in departments if dept]  # Remove empty values
        
        return Response({'departments': sorted(departments)})
    
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """
        Get list of all user roles
        GET /api/v1/users/roles/
        """
        from api.permissions import RoleBasedPermission
        
        roles = [
            {'value': role, 'label': role.title(), 'level': level}
            for role, level in RoleBasedPermission.ROLE_HIERARCHY.items()
        ]
        
        return Response({'roles': roles})
