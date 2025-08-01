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
    """Main dashboard page with role-specific layouts using service layer"""
    
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
        
        # Use the new dashboard service with strategy pattern
        from core.services import DashboardService
        dashboard_context = DashboardService.get_dashboard_context(self.request.user)
        
        # Add base navigation context
        dashboard_context.update({
            'page_title': 'Dashboard',
            'active_nav': 'dashboard',
        })
        
        context.update(dashboard_context)
        return context

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
    """User profile page using UserService"""
    template_name = 'pages/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use UserService to get profile data
        from core.services import UserService
        user_service = UserService(self.request.user)
        profile_data = user_service.get_user_profile_data()
        
        context.update({
            'page_title': 'Profile',
            'active_nav': 'profile',
            **profile_data,
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


class ShiftSwapRequestView(BaseView):
    """Shift swap request page for users"""
    template_name = 'pages/shift_swap_request.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Shift Swap Requests',
            'active_nav': 'swap_requests',
        })
        return context


class ShiftSwapApprovalView(BaseView):
    """Shift swap approval page for managers"""
    template_name = 'pages/shift_swap_approval.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Check if user has manager permissions
        if user.role not in ['MANAGER', 'ADMIN']:
            # Could redirect or show limited view
            pass
            
        context.update({
            'page_title': 'Shift Swap Approvals',
            'active_nav': 'swap_approvals',
        })
        return context
