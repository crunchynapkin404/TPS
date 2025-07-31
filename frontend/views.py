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
    """Main dashboard page with real API data integration"""
    template_name = 'pages/dashboard.html'
    
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
        
        # Upcoming shifts (next 5)
        upcoming_shifts = Assignment.objects.filter(
            Q(user=user) | Q(shift__planning_period__teams__in=user_teams),
            shift__start_datetime__gt=timezone.now()
        ).select_related('user', 'shift__template', 'shift__template__category').order_by('shift__start_datetime')[:5]
        
        # Pending approvals (if user is manager/team leader)
        pending_approvals_count = 0
        pending_approvals_list = []
        if user.is_staff or Team.objects.filter(team_leader=user).exists():
            # Get teams led by this user
            led_teams = Team.objects.filter(team_leader=user)
            pending_approvals_queryset = Assignment.objects.filter(
                shift__planning_period__teams__in=led_teams,
                status='pending_confirmation'
            ).select_related('user', 'shift__template')[:10]
            pending_approvals_count = pending_approvals_queryset.count()
            pending_approvals_list = list(pending_approvals_queryset)
        
        # Active team members count
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        )
        active_members = User.objects.filter(
            team_memberships__team__in=user_teams,
            is_active=True
        ).distinct().count()
        
        # Total assignments this month
        month_start = today.replace(day=1)
        monthly_assignments = Assignment.objects.filter(
            shift__start_datetime__gte=month_start,
            shift__start_datetime__lt=month_start + timedelta(days=32),
            status__in=['confirmed', 'completed']
        ).count()
        
        # System health (simplified calculation)
        failed_assignments = Assignment.objects.filter(
            status__in=['declined', 'no_show', 'cancelled'],
            assigned_at__gte=today - timedelta(days=7)
        ).count()
        total_assignments = Assignment.objects.filter(
            assigned_at__gte=today - timedelta(days=7)
        ).count()
        system_health = 100.0 if total_assignments == 0 else ((total_assignments - failed_assignments) / total_assignments) * 100
        
        # Fairness score (simplified calculation based on assignment distribution)
        try:
            # Calculate basic fairness based on assignment distribution
            user_assignment_counts = Assignment.objects.filter(
                shift__start_datetime__gte=month_start,
                status__in=['confirmed', 'completed']
            ).values('user').annotate(
                assignment_count=Count('id')
            ).values_list('assignment_count', flat=True)
            
            if user_assignment_counts:
                avg_assignments = sum(user_assignment_counts) / len(user_assignment_counts)
                max_deviation = max(abs(count - avg_assignments) for count in user_assignment_counts)
                fairness_score = max(0, 100 - (max_deviation / avg_assignments * 100)) if avg_assignments > 0 else 100
            else:
                fairness_score = 100.0
        except Exception:
            fairness_score = 85.0  # Default if calculation fails
        
        # Recent activity (last 10 assignments)
        recent_assignments = Assignment.objects.filter(
            Q(user=user) | Q(shift__planning_period__teams__in=user_teams)
        ).select_related('user', 'shift__template', 'shift__template__category').order_by('-assigned_at')[:10]
        
        # Team workload data
        teams_data = []
        for team in user_teams:
            # Get current week assignments for this team
            team_assignments = Assignment.objects.filter(
                shift__planning_period__teams=team,
                shift__start_datetime__gte=current_week_start,
                shift__start_datetime__lte=current_week_end,
                status__in=['confirmed', 'pending_confirmation']
            ).count()
            
            # Calculate team capacity (simplified)
            team_members_count = TeamMembership.objects.filter(team=team, is_active=True).count()
            team_capacity = team_members_count * 5  # Assuming 5 shifts per week max per member
            workload_percentage = (team_assignments / team_capacity * 100) if team_capacity > 0 else 0
            
            teams_data.append({
                'team': team,
                'workload_percentage': min(workload_percentage, 100),
                'workload_status': 'danger' if workload_percentage > 90 else 'warning' if workload_percentage > 70 else 'success'
            })
        
        context.update({
            'page_title': 'Dashboard',
            'active_nav': 'dashboard',
            'today': today,
            # Real dashboard statistics
            'my_upcoming_shifts': upcoming_shifts,
            'pending_approvals': pending_approvals_count,
            'pending_approvals_list': pending_approvals_list,
            'active_members': active_members,
            'monthly_assignments': monthly_assignments,
            'system_health': round(system_health, 1),
            'fairness_score': round(fairness_score, 1),
            # Activity data
            'recent_assignments': recent_assignments,
            'teams_data': teams_data,
            # Additional metrics
            'week_start': current_week_start,
            'week_end': current_week_end,
        })
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
    """Schedule calendar page with timeline view - desktop optimized"""
    template_name = 'pages/schedule.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date and week range
        today = timezone.now().date()
        
        # Get week parameter or default to current week
        week_offset = int(self.request.GET.get('week', 0))
        current_week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_days = [current_week_start + timedelta(days=i) for i in range(7)]
        
        # Get all teams and their members
        user = self.request.user
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        ).prefetch_related('memberships__user')
        
        # Get all team members for vertical display
        team_members = []
        for team in user_teams:
            for membership in team.memberships.all():
                team_members.append({
                    'user': membership.user,
                    'team': team,
                    'role': membership.role
                })
        
        # Get all shifts for the week
        week_shifts = ShiftInstance.objects.filter(
            start_datetime__date__gte=current_week_start,
            start_datetime__date__lte=current_week_start + timedelta(days=6),
            planning_period__teams__in=user_teams
        ).select_related('template', 'template__category')
        
        # Get assignments for the week
        week_assignments = Assignment.objects.filter(
            shift__in=week_shifts,
            status__in=['confirmed', 'pending_confirmation']
        ).select_related('user', 'shift')
        
        # Create timeline data structure: member -> day -> assignments
        timeline_data = {}
        for member_data in team_members:
            member_id = member_data['user'].id
            timeline_data[member_id] = {
                'member': member_data,
                'days': {}
            }
            
            # Initialize each day
            for day in week_days:
                timeline_data[member_id]['days'][day.isoformat()] = []
        
        # Populate assignments into timeline
        for assignment in week_assignments:
            if assignment.user and assignment.user.id in timeline_data:
                shift_date = assignment.shift.start_datetime.date()
                day_key = shift_date.isoformat()
                if day_key in timeline_data[assignment.user.id]['days']:
                    timeline_data[assignment.user.id]['days'][day_key].append(assignment)
        
        # Calculate week statistics
        total_shifts = week_shifts.count()
        assigned_shifts = week_assignments.filter(status='confirmed').count()
        coverage_percentage = (assigned_shifts / total_shifts * 100) if total_shifts > 0 else 100
        
        context.update({
            'page_title': 'Schedule Calendar',
            'active_nav': 'schedule',
            'week_start': current_week_start,
            'week_days': week_days,
            'timeline_data': timeline_data,
            'team_members': team_members,
            'user_teams': user_teams,
            'week_shifts': week_shifts,
            'total_shifts': total_shifts,
            'assigned_shifts': assigned_shifts,
            'coverage_percentage': round(coverage_percentage, 1),
            'week_offset': week_offset,
            'prev_week': week_offset - 1,
            'next_week': week_offset + 1,
        })
        return context


class ScheduleNewView(TemplateView):  # Temporarily removed LoginRequiredMixin for debugging
    """New clean Tailwind-based schedule calendar"""
    template_name = 'pages/schedule_new.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date
        today = timezone.now().date()
        
        # For debugging, get a test user
        from apps.accounts.models import User
        try:
            user = User.objects.get(username='user2')
        except User.DoesNotExist:
            user = User.objects.first()
            
        # Get user's teams for filtering
        user_teams = Team.objects.filter(
            Q(memberships__user=user) | Q(team_leader=user)
        )
        
        # Debug: print user and teams info
        print(f"DEBUG: User = {user.username if user else 'None'}")
        print(f"DEBUG: User teams = {[(t.pk, t.name) for t in user_teams]}")
        
        context.update({
            'page_title': 'Team Schedule',
            'active_nav': 'schedule',
            'current_date': today,
            'user_teams': user_teams,
            'debug_user': user.username if user else 'None',
            'debug_teams': [(t.pk, t.name) for t in user_teams],
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
