from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Q, Sum
from datetime import datetime, timedelta

from apps.teams.models import Team, TeamMembership
from apps.accounts.models import User
from apps.scheduling.models import ShiftTemplate, ShiftInstance, PlanningPeriod
from apps.assignments.models import Assignment


class BaseView(LoginRequiredMixin, TemplateView):
    """Base view for all authenticated pages"""
    login_url = '/login/'


class DashboardView(BaseView):
    """Main dashboard page with role-specific layouts"""
    
    def get_template_names(self):
        """Return role-specific template based on user role"""
        user_role = self.request.user.role
        template_map = {
            'ADMIN': 'pages/dashboard_admin.html',
            'MANAGER': 'pages/dashboard_manager.html', 
            'PLANNER': 'pages/dashboard_planner.html',
            'USER': 'pages/dashboard_user.html',
        }
        return [template_map.get(user_role, 'pages/dashboard.html')]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date/time for calculations
        now = timezone.now()
        today = now.date()
        current_week_start = today - timedelta(days=today.weekday())
        current_week_end = current_week_start + timedelta(days=6)
        
        # Real data for stats cards
        user = self.request.user
        
        # Get user's teams
        user_teams = Team.objects.filter(
            memberships__user=user
        )
        
        # Base context for all roles
        base_context = {
            'page_title': 'Dashboard',
            'active_nav': 'dashboard',
            'today': today,
            'week_start': current_week_start,
            'week_end': current_week_end,
        }
        
        # Role-specific context
        if user.role == 'ADMIN':
            context.update(self._get_admin_context(user, today, current_week_start, current_week_end))
        elif user.role == 'MANAGER':
            context.update(self._get_manager_context(user, today, current_week_start, current_week_end, user_teams))
        elif user.role == 'PLANNER':
            context.update(self._get_planner_context(user, today, current_week_start, current_week_end, user_teams))
        else:  # USER
            context.update(self._get_user_context(user, today, current_week_start, current_week_end, user_teams))
            
        context.update(base_context)
        return context
    
    def _get_admin_context(self, user, today, week_start, week_end):
        """Context for admin dashboard - system overview"""
        from apps.leave_management.models import LeaveRequest
        
        # System-wide statistics
        total_users = User.objects.filter(is_active=True).count()
        total_teams = Team.objects.count()
        total_assignments_this_week = Assignment.objects.filter(
            shift__start_datetime__gte=week_start,
            shift__start_datetime__lte=week_end
        ).count()
        
        # System health metrics
        failed_assignments = Assignment.objects.filter(
            status__in=['declined', 'no_show', 'cancelled'],
            assigned_at__gte=today - timedelta(days=7)
        ).count()
        total_assignments = Assignment.objects.filter(
            assigned_at__gte=today - timedelta(days=7)
        ).count()
        system_health = 100.0 if total_assignments == 0 else ((total_assignments - failed_assignments) / total_assignments) * 100
        
        # Leave requests needing attention
        pending_leave_requests = LeaveRequest.objects.filter(
            status__in=['submitted', 'pending_hr']
        ).count()
        
        # Recent system activity
        recent_activity = Assignment.objects.select_related(
            'user', 'shift__template'
        ).order_by('-assigned_at')[:10]
        
        return {
            'dashboard_type': 'admin',
            'total_users': total_users,
            'total_teams': total_teams,
            'total_assignments_this_week': total_assignments_this_week,
            'system_health': round(system_health, 1),
            'pending_leave_requests': pending_leave_requests,
            'recent_activity': recent_activity,
        }
    
    def _get_manager_context(self, user, today, week_start, week_end, user_teams):
        """Context for manager dashboard - team management focus"""
        from apps.leave_management.models import LeaveRequest
        
        # Teams managed by this user
        managed_teams = Team.objects.filter(team_leader=user)
        
        # Pending approvals across managed teams
        pending_approvals = Assignment.objects.filter(
            shift__planning_period__teams__in=managed_teams,
            status='pending_confirmation'
        ).select_related('user', 'shift__template')[:10]
        
        # Leave requests pending manager approval
        pending_leave_approvals = LeaveRequest.objects.filter(
            status__in=['submitted', 'pending_manager'],
            user__team_memberships__team__in=managed_teams
        ).distinct().select_related('user', 'leave_type')[:10]
        
        # Team performance metrics
        team_stats = []
        for team in managed_teams:
            team_members = User.objects.filter(team_memberships__team=team).count()
            this_week_assignments = Assignment.objects.filter(
                shift__planning_period__teams=team,
                shift__start_datetime__gte=week_start,
                shift__start_datetime__lte=week_end
            ).count()
            
            team_stats.append({
                'team': team,
                'members': team_members,
                'this_week_assignments': this_week_assignments,
            })
        
        return {
            'dashboard_type': 'manager',
            'managed_teams': managed_teams,
            'pending_approvals': pending_approvals,
            'pending_leave_approvals': pending_leave_approvals,
            'team_stats': team_stats,
            'total_managed_teams': managed_teams.count(),
        }
    
    def _get_planner_context(self, user, today, week_start, week_end, user_teams):
        """Context for planner dashboard - planning and scheduling focus"""
        
        # Planning periods that need attention
        planning_periods = PlanningPeriod.objects.filter(
            teams__in=user_teams,
            start_date__gte=today,
            is_published=False
        ).distinct()[:5]
        
        # Unassigned shifts
        unassigned_shifts = ShiftInstance.objects.filter(
            planning_period__teams__in=user_teams,
            assignments__isnull=True,
            start_datetime__gte=today
        ).select_related('template', 'planning_period')[:10]
        
        # Planning workload analysis
        planning_advice = self._generate_planning_advice(user_teams, today)
        
        # Recent planning activity
        recent_planning_activity = Assignment.objects.filter(
            shift__planning_period__teams__in=user_teams
        ).select_related('user', 'shift__template').order_by('-assigned_at')[:10]
        
        return {
            'dashboard_type': 'planner',
            'planning_periods': planning_periods,
            'unassigned_shifts': unassigned_shifts,
            'planning_advice': planning_advice,
            'recent_planning_activity': recent_planning_activity,
        }
    
    def _get_user_context(self, user, today, week_start, week_end, user_teams):
        """Context for regular user dashboard - personal focus"""
        from apps.leave_management.models import LeaveRequest
        
        # Personal upcoming shifts
        upcoming_shifts = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gt=timezone.now()
        ).select_related('shift__template').order_by('shift__start_datetime')[:8]
        
        # Personal leave requests
        my_leave_requests = LeaveRequest.objects.filter(
            user=user
        ).select_related('leave_type').order_by('-created_at')[:5]
        
        # NEW: Today's engineer assignments (real data)
        # Get incident engineer assigned for today
        incident_engineer_today = Assignment.objects.filter(
            shift__date=today,
            shift__template__category__name='INCIDENT',
            status__in=['confirmed', 'completed', 'in_progress']
        ).select_related('user', 'shift__template').first()
        
        # Get waakdienst (on-call) engineer assigned for today
        waakdienst_engineer_today = Assignment.objects.filter(
            shift__date=today,
            shift__template__category__name='WAAKDIENST',
            status__in=['confirmed', 'completed', 'in_progress']
        ).select_related('user', 'shift__template').first()
        
        # Get total working engineers today (distinct count)
        total_working_today = Assignment.objects.filter(
            shift__date=today,
            status__in=['confirmed', 'completed', 'in_progress']
        ).values('user').distinct().count()
        
        # Personal advice/recommendations
        personal_advice = self._generate_personal_advice(user, today)
        
        return {
            'dashboard_type': 'user',
            'upcoming_shifts': upcoming_shifts,
            'my_leave_requests': my_leave_requests,
            'incident_engineer_today': incident_engineer_today,
            'waakdienst_engineer_today': waakdienst_engineer_today,
            'total_working_today': total_working_today,
            'personal_advice': personal_advice,
        }
    
    def _generate_planning_advice(self, user_teams, today):
        """Generate intelligent planning advice"""
        advice = []
        
        # Check for understaffed periods
        for team in user_teams[:3]:  # Limit for performance
            upcoming_shifts = ShiftInstance.objects.filter(
                planning_period__teams=team,
                start_datetime__gte=today,
                start_datetime__lte=today + timedelta(days=14),
                assignments__isnull=True
            ).count()
            
            if upcoming_shifts > 5:
                advice.append({
                    'type': 'warning',
                    'title': f'Understaffed: {team.name}',
                    'message': f'{upcoming_shifts} unassigned shifts in the next 2 weeks',
                    'action': 'Review staffing levels'
                })
        
        # Check for workload imbalance
        if not advice:  # Only if no critical issues
            advice.append({
                'type': 'info',
                'title': 'Workload Distribution',
                'message': 'Consider rotating weekend assignments for better work-life balance',
                'action': 'View fairness report'
            })
        
        return advice
    
    def _generate_personal_advice(self, user, today):
        """Generate personal advice for users"""
        advice = []
        
        # Check upcoming workload
        next_week_shifts = Assignment.objects.filter(
            user=user,
            shift__start_datetime__gte=today + timedelta(days=7),
            shift__start_datetime__lte=today + timedelta(days=14)
        ).count()
        
        if next_week_shifts > 5:
            advice.append({
                'type': 'info',
                'title': 'Busy Week Ahead',
                'message': f'You have {next_week_shifts} shifts scheduled next week',
                'action': 'Consider planning rest time'
            })
        
        # Check leave balance
        from apps.leave_management.models import LeaveBalance
        try:
            annual_balance = LeaveBalance.objects.get(
                user=user,
                leave_type__code='ANNUAL',
                year=today.year
            )
            if annual_balance.remaining > 10:
                advice.append({
                    'type': 'success', 
                    'title': 'Plan Your Vacation',
                    'message': f'You have {annual_balance.remaining:.1f} days of annual leave remaining',
                    'action': 'Book time off'
                })
        except LeaveBalance.DoesNotExist:
            pass
        
        return advice


class TeamsView(BaseView):
    """Teams overview page with enhanced management features"""
    template_name = 'pages/teams.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Teams',
            'active_nav': 'teams',
            'teams': Team.objects.all()
        })
        return context


class TeamDetailView(BaseView):
    """Individual team detail page"""
    template_name = 'pages/team_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = get_object_or_404(Team, id=kwargs['team_id'])
        context.update({
            'page_title': f'Team: {team.name}',
            'active_nav': 'teams',
            'team': team,
        })
        return context


class ScheduleView(BaseView):
    """Schedule calendar page with timeline view - production ready"""
    template_name = 'pages/schedule.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date
        today = timezone.now().date()
        
        # Get user's teams for filtering
        user = self.request.user
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).distinct()
        
        context.update({
            'page_title': 'Team Schedule',
            'active_nav': 'schedule',
            'current_date': today,
            'user_teams': user_teams,
        })
        return context




class AssignmentsView(BaseView):
    """Assignments management page"""
    template_name = 'pages/assignments.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Assignments',
            'active_nav': 'assignments',
        })
        return context


class PlanningView(BaseView):
    """Planning generation and management page with wizard"""
    template_name = 'pages/planning.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Planning Wizard',
            'active_nav': 'planning',
        })
        return context


class AnalyticsView(BaseView):
    """Analytics and reporting page"""
    template_name = 'pages/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Get user's teams
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).distinct()
        
        # Calculate key metrics
        assignments_this_month = Assignment.objects.filter(
            shift__start_datetime__date__gte=month_start,
            status__in=['confirmed', 'completed']
        )
        
        # Fairness score calculation
        user_assignment_counts = assignments_this_month.values('user').annotate(
            assignment_count=Count('id')
        ).values_list('assignment_count', flat=True)
        
        if user_assignment_counts:
            avg_assignments = sum(user_assignment_counts) / len(user_assignment_counts)
            max_deviation = max(abs(count - avg_assignments) for count in user_assignment_counts) if avg_assignments > 0 else 0
            fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
        else:
            fairness_score = 100.0
        
        # Average workload
        active_users = User.objects.filter(
            team_memberships__team__in=user_teams,
            is_active=True
        ).distinct().count()
        avg_workload = (assignments_this_month.count() / active_users) if active_users > 0 else 0
        
        # Coverage rate
        from apps.scheduling.models import ShiftInstance
        total_shifts = ShiftInstance.objects.filter(
            start_datetime__date__gte=month_start,
            planning_period__teams__in=user_teams
        ).count()
        covered_shifts = assignments_this_month.count()
        coverage_rate = (covered_shifts / total_shifts * 100) if total_shifts > 0 else 0
        
        # Planning efficiency
        total_assignments = Assignment.objects.filter(
            shift__start_datetime__date__gte=month_start
        ).count()
        confirmed_assignments = Assignment.objects.filter(
            shift__start_datetime__date__gte=month_start,
            status='confirmed'
        ).count()
        planning_efficiency = (confirmed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        context.update({
            'page_title': 'Analytics',
            'active_nav': 'analytics',
            'fairness_score': round(fairness_score, 1),
            'average_workload': round(avg_workload, 1),
            'coverage_rate': round(coverage_rate, 1),
            'planning_efficiency': round(planning_efficiency, 1),
        })
        return context


class ProfileView(BaseView):
    """User profile page"""
    template_name = 'pages/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Profile',
            'active_nav': 'profile',
        })
        return context





class LoginView(DjangoLoginView):
    """Login page"""
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Always redirect to dashboard after login"""
        return '/'


class LogoutView(DjangoLogoutView):
    """Logout view with proper POST security"""
    next_page = reverse_lazy('frontend:login')
