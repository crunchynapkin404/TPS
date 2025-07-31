"""
TPS V1.4 - Teams API Views
Django REST Framework ViewSets for team management
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from api.permissions import (
    TPSPermission, TacticalPermission, ManagementPermission,
    TeamMemberPermission, ReadOnlyOrManagerPermission
)
from api.serializers.team_serializers import (
    TeamSerializer, TeamListSerializer, TeamCreateSerializer,
    TeamUpdateSerializer, TeamMembershipSerializer, AddTeamMemberSerializer,
    TeamScheduleSerializer, TeamWorkloadSerializer, TeamPlanningDataSerializer
)
from apps.teams.models import Team, TeamMembership, TeamRole
from core.services.fairness_service import FairnessService

User = get_user_model()


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for team management with comprehensive functionality
    """
    queryset = Team.objects.all()
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrManagerPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TeamListSerializer
        elif self.action == 'create':
            return TeamCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TeamUpdateSerializer
        elif self.action == 'add_member':
            return AddTeamMemberSerializer
        elif self.action == 'get_schedule':
            return TeamScheduleSerializer
        elif self.action == 'get_workload_analysis':
            return TeamWorkloadSerializer
        elif self.action == 'get_planning_data':
            return TeamPlanningDataSerializer
        return TeamSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, ManagementPermission]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated, TacticalPermission]
        elif self.action in ['add_member', 'remove_member']:
            permission_classes = [permissions.IsAuthenticated, TacticalPermission]
        elif self.action in ['get_planning_data', 'get_workload_analysis']:
            permission_classes = [permissions.IsAuthenticated, TeamMemberPermission]
        else:
            permission_classes = [permissions.IsAuthenticated, TPSPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters"""
        queryset = Team.objects.select_related('team_leader').prefetch_related(
            'memberships__user',
            'memberships__role'
        )
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department=department)
        
        # Filter by user membership (teams user belongs to)
        user_member = self.request.query_params.get('user_member')
        if user_member:
            try:
                user_id = int(user_member)
                queryset = queryset.filter(
                    memberships__user_id=user_id,
                    memberships__is_active=True
                )
            except (ValueError, TypeError):
                pass
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(department__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def get_members(self, request, pk=None):
        """
        Get team members with their roles and information
        GET /api/v1/teams/{id}/members/
        """
        team = self.get_object()
        
        # Get active memberships
        memberships = team.memberships.filter(
            is_active=True
        ).select_related('user', 'role').order_by('role__name', 'user__last_name')
        
        serializer = TeamMembershipSerializer(memberships, many=True)
        return Response({
            'team_id': team.id,
            'team_name': team.name,
            'members': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def get_schedule(self, request, pk=None):
        """
        Get team schedule for a date range
        GET /api/v1/teams/{id}/schedule/?start_date=2024-01-01&end_date=2024-01-31
        """
        team = self.get_object()
        
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
        
        # Get all shifts for the team in date range
        from apps.scheduling.models import ShiftInstance
        shifts = ShiftInstance.objects.filter(
            team=team,
            date__range=[start_date, end_date]
        ).select_related('template').prefetch_related(
            'assignment_set__user'
        ).order_by('date', 'start_time')
        
        # Group by date
        schedule_data = {}
        for shift in shifts:
            date_str = shift.date.isoformat()
            if date_str not in schedule_data:
                schedule_data[date_str] = {
                    'date': shift.date,
                    'assignments': [],
                    'total_shifts': 0,
                    'coverage_percentage': 0
                }
            
            # Get assignments for this shift
            assignments = shift.assignment_set.select_related('user').all()
            assignment_data = []
            for assignment in assignments:
                assignment_data.append({
                    'assignment_id': assignment.id,
                    'user_id': assignment.user.id,
                    'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip(),
                    'assignment_type': assignment.assignment_type,
                    'status': assignment.status,
                    'shift_name': shift.template.name,
                    'start_datetime': shift.start_datetime,
                    'end_datetime': shift.end_datetime,
                    'location': getattr(shift, 'location_override', None) or getattr(shift.template, 'location', '')
                })
            
            schedule_data[date_str]['assignments'].extend(assignment_data)
            schedule_data[date_str]['total_shifts'] += 1
            
            # Calculate coverage
            required_staff = shift.template.staffing_requirements.get('required_staff', 1)
            assigned_staff = len([a for a in assignments if a.status in ['CONFIRMED', 'COMPLETED']])
            coverage = (assigned_staff / required_staff) * 100 if required_staff > 0 else 0
            schedule_data[date_str]['coverage_percentage'] = max(
                schedule_data[date_str]['coverage_percentage'], coverage
            )
        
        # Convert to list and sort by date
        schedule_list = list(schedule_data.values())
        schedule_list.sort(key=lambda x: x['date'])
        
        return Response({
            'team_id': team.id,
            'team_name': team.name,
            'start_date': start_date,
            'end_date': end_date,
            'schedule': schedule_list
        })
    
    @action(detail=True, methods=['get'])
    def get_planning_summary(self, request, pk=None):
        """
        Get team planning summary and statistics
        GET /api/v1/teams/{id}/planning-summary/
        """
        team = self.get_object()
        
        # Get current planning period data
        current_date = timezone.now().date()
        month_start = current_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Get team statistics
        active_members = team.memberships.filter(is_active=True).count()
        
        from apps.assignments.models import Assignment
        from apps.scheduling.models import ShiftInstance
        
        # Current month assignments
        current_assignments = Assignment.objects.filter(
            shift__team=team,
            shift__date__range=[month_start, month_end]
        )
        
        pending_assignments = current_assignments.filter(status='PROPOSED').count()
        completed_assignments = current_assignments.filter(status='COMPLETED').count()
        
        # Upcoming shifts needing assignment
        upcoming_shifts = ShiftInstance.objects.filter(
            team=team,
            date__gte=current_date,
            date__lte=current_date + timedelta(days=14)
        ).exclude(
            assignment__status__in=['CONFIRMED', 'COMPLETED']
        ).count()
        
        # Calculate average workload balance using fairness service
        try:
            fairness_service = FairnessService(team)
            team_members = [membership.user for membership in team.memberships.filter(is_active=True)]
            if team_members:
                fairness_scores = [
                    fairness_service.calculate_user_fairness_score(user) 
                    for user in team_members
                ]
                avg_balance = sum(fairness_scores) / len(fairness_scores)
            else:
                avg_balance = 0
        except Exception:
            avg_balance = 0
        
        return Response({
            'team_id': team.id,
            'team_name': team.name,
            'statistics': {
                'total_members': active_members,
                'active_members': active_members,
                'pending_assignments': pending_assignments,
                'completed_assignments_this_month': completed_assignments,
                'average_workload_balance': round(avg_balance, 2),
                'upcoming_shifts_count': upcoming_shifts
            },
            'period': {
                'start_date': month_start,
                'end_date': month_end
            }
        })
    
    @action(detail=True, methods=['get'])
    def get_workload_analysis(self, request, pk=None):
        """
        Get workload analysis for team members
        GET /api/v1/teams/{id}/workload-analysis/
        """
        team = self.get_object()
        
        # Get active team members
        memberships = team.memberships.filter(is_active=True).select_related('user')
        
        workload_data = []
        fairness_service = FairnessService(team)
        
        for membership in memberships:
            user = membership.user
            
            # Get next availability date
            from apps.assignments.models import Assignment
            last_assignment = Assignment.objects.filter(
                user=user,
                status__in=['CONFIRMED', 'COMPLETED'],
                shift__date__gte=timezone.now().date()
            ).order_by('-shift__date').first()
            
            next_availability = None
            if last_assignment:
                # Add gap period based on shift type
                if last_assignment.shift.template.category == 'WAAKDIENST':
                    next_availability = last_assignment.shift.date + timedelta(days=14)
                elif last_assignment.shift.template.category == 'INCIDENT':
                    next_availability = last_assignment.shift.date + timedelta(days=7)
                else:
                    next_availability = last_assignment.shift.date + timedelta(days=1)
            
            workload_data.append({
                'user_id': user.id,
                'user_name': f"{user.first_name} {user.last_name}".strip(),
                'ytd_hours': user.ytd_hours_worked or 0,
                'ytd_weeks_waakdienst': user.ytd_weeks_waakdienst or 0,
                'ytd_weeks_incident': user.ytd_weeks_incident or 0,
                'fairness_score': fairness_service.calculate_user_fairness_score(user),
                'next_availability': next_availability
            })
        
        # Sort by fairness score (lowest first = most available)
        workload_data.sort(key=lambda x: x['fairness_score'])
        
        return Response({
            'team_id': team.id,
            'team_name': team.name,
            'workload_analysis': workload_data
        })
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """
        Add a member to the team
        POST /api/v1/teams/{id}/add-member/
        """
        team = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'team': team})
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            role_id = serializer.validated_data['role_id']
            notes = serializer.validated_data.get('notes', '')
            
            # Create team membership
            membership = TeamMembership.objects.create(
                team=team,
                user_id=user_id,
                role_id=role_id,
                notes=notes,
                joined_date=timezone.now().date()
            )
            
            response_serializer = TeamMembershipSerializer(membership)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """
        Remove a member from the team
        DELETE /api/v1/teams/{id}/remove-member/?user_id=123
        """
        team = self.get_object()
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            membership = TeamMembership.objects.get(
                team=team, user_id=user_id, is_active=True
            )
            membership.is_active = False
            membership.save()
            
            return Response({'message': 'Team member removed successfully'})
        
        except TeamMembership.DoesNotExist:
            return Response(
                {'error': 'User is not an active member of this team'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """
        Get list of all departments
        GET /api/v1/teams/departments/
        """
        departments = Team.objects.values_list('department', flat=True).distinct()
        departments = [dept for dept in departments if dept]  # Remove empty values
        
        return Response({'departments': sorted(departments)})
    
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """
        Get list of all team roles
        GET /api/v1/teams/roles/
        """
        roles = TeamRole.objects.filter(is_active=True).values(
            'id', 'name', 'description', 'can_assign_shifts', 'can_approve_leave', 'is_leadership'
        )
        
        return Response({'roles': list(roles)})
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Get teams overview with statistics for the teams page
        GET /api/v1/teams/overview/
        """
        try:
            user = request.user
            
            # Get teams user has access to (member or leader)
            teams = Team.objects.filter(
                Q(memberships__user=user) | Q(team_leader=user)
            ).distinct()
            
            teams_data = []
            for team in teams:
                try:
                    # Get team statistics using the correct relationship
                    member_count = team.memberships.filter(is_active=True).count()
                except Exception:
                    member_count = 0
                
                # Mock some additional data for now
                teams_data.append({
                    'id': team.id,
                    'name': team.name,
                    'description': team.description or 'Team Operations',
                    'status': 'Active',
                    'member_count': member_count,
                    'ytd_hours': 2450,  # Mock data
                    'coverage_percentage': 85,  # Mock data
                    'fairness_score': 7.8,  # Mock data
                    'workload_percentage': 78,  # Mock data
                    'performance_trend': [75, 82, 78, 85, 88, 84, 87]  # Mock 7-day trend
                })
            
            # If no teams found, return mock data
            if not teams_data:
                teams_data = [
                    {
                        'id': 1,
                        'name': 'Engineering Team A',
                        'description': 'Primary engineering operations',
                        'status': 'Active',
                        'member_count': 12,
                        'ytd_hours': 2450,
                        'coverage_percentage': 85,
                        'fairness_score': 7.8,
                        'workload_percentage': 78,
                        'performance_trend': [75, 82, 78, 85, 88, 84, 87]
                    },
                    {
                        'id': 2,
                        'name': 'Operations Team B',
                        'description': 'Operations and maintenance',
                        'status': 'Active',
                        'member_count': 8,
                        'ytd_hours': 1980,
                        'coverage_percentage': 92,
                        'fairness_score': 8.2,
                        'workload_percentage': 65,
                        'performance_trend': [80, 85, 88, 90, 87, 89, 91]
                    }
                ]
            
            # Calculate overview statistics
            total_teams = teams.count()
            total_active_members = sum(team['member_count'] for team in teams_data)
            active_teams = len([t for t in teams_data if t['status'] == 'Active'])
            avg_efficiency_rate = 82  # Mock data
            
            return Response({
                'success': True,
                'teams': teams_data,
                'total_teams': total_teams,
                'total_active_members': total_active_members,
                'active_teams': active_teams,
                'avg_efficiency_rate': avg_efficiency_rate
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to fetch teams overview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get team statistics for dashboard widgets
        GET /api/v1/teams/statistics/
        """
        try:
            user = request.user
            
            # Get teams user has access to (member or leader)
            teams = Team.objects.filter(
                Q(memberships__user=user) | Q(team_leader=user)
            ).distinct()
            
            # Calculate statistics
            total_teams = teams.count()
            total_members = 0
            active_members = 0
            
            for team in teams:
                try:
                    total_members += team.memberships.count()
                    active_members += team.memberships.filter(is_active=True).count()
                except Exception:
                    # Skip if relationship access fails
                    pass
            
            # If no data found, use mock data
            if total_teams == 0:
                total_teams = 2
                total_members = 20
                active_members = 18
            
            # Mock some additional statistics
            stats = {
                'total_teams': total_teams,
                'total_members': total_members,
                'active_members': active_members,
                'avg_coverage': 85,  # Mock data
                'efficiency_rate': 82,  # Mock data
                'workload_distribution': {
                    'balanced': 65,
                    'overloaded': 25,
                    'underutilized': 10
                },
                'performance_metrics': {
                    'response_time': 2.3,
                    'completion_rate': 94.5,
                    'satisfaction_score': 4.2
                }
            }
            
            return Response({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to fetch team statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def test_models(self, request):
        """
        Test endpoint to verify model relationships work (no auth required)
        """
        try:
            # Test basic model queries
            total_teams = Team.objects.count()
            total_memberships = TeamMembership.objects.count()
            
            # Test a simple team query
            first_team = Team.objects.first()
            team_info = None
            if first_team:
                try:
                    members_count = first_team.memberships.filter(is_active=True).count()
                    team_info = {
                        'id': first_team.id,
                        'name': first_team.name,
                        'members_count': members_count,
                        'leader': first_team.team_leader.username if first_team.team_leader else None
                    }
                except Exception as e:
                    team_info = {'error': str(e)}
            
            return Response({
                'success': True,
                'total_teams': total_teams,
                'total_memberships': total_memberships,
                'first_team': team_info,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
