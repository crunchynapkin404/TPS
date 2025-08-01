"""
TPS V1.4 - Leave Management Views
Complete leave request system with approval workflow
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.utils import timezone
from django.urls import reverse_lazy
from datetime import date, timedelta
import json

from .models import LeaveType, LeaveRequest, RecurringLeave, LeaveBalance
from .forms import LeaveRequestForm, RecurringLeaveForm
from apps.accounts.models import User


class LeaveOverviewView(LoginRequiredMixin, ListView):
    """Main leave management overview page"""
    template_name = 'leave_management/overview.html'
    context_object_name = 'leave_requests'
    
    def get_queryset(self):
        user = self.request.user
        if user.is_manager() or user.is_admin():
            # Managers see all requests in their teams
            return LeaveRequest.objects.all().select_related('user', 'leave_type').order_by('-created_at')
        else:
            # Users see only their own requests
            return LeaveRequest.objects.filter(user=user).select_related('leave_type').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's leave balances for current year - OPTIMIZED with single query
        current_year = timezone.now().year
        leave_balances = LeaveBalance.objects.filter(
            user=user,
            year=current_year
        ).select_related('leave_type')
        
        # Get base queryset once to avoid repeated evaluation
        base_queryset = self.get_queryset()
        
        # Get pending approvals if user is manager - OPTIMIZED with better select_related
        pending_approvals = []
        if user.is_manager() or user.is_admin():
            pending_approvals = LeaveRequest.objects.filter(
                status__in=['submitted', 'pending_manager', 'pending_hr']
            ).select_related(
                'user', 'leave_type'
            ).prefetch_related(
                'user__team_memberships__team'  # For team-based filtering if needed
            ).order_by('start_date')
        
        # Get upcoming leave - OPTIMIZED query
        upcoming_leave = LeaveRequest.objects.filter(
            user=user,
            status='approved',
            start_date__gte=timezone.now().date()
        ).select_related('leave_type').order_by('start_date')[:5]
        
        # Statistics - OPTIMIZED with combined aggregations
        from django.db.models import Count, Case, When, Sum as DBSum
        
        # Get request counts and leave balance totals in optimized queries
        request_stats = base_queryset.aggregate(
            total_requests=Count('id'),
            pending_requests=Count('id', filter=Q(
                status__in=['submitted', 'pending_manager', 'pending_hr']
            )),
            approved_requests=Count('id', filter=Q(status='approved'))
        )
        
        balance_stats = leave_balances.aggregate(
            used_days_ytd=DBSum('used'),
            pending_days=DBSum('pending')
        )
        
        stats = {
            'total_requests': request_stats['total_requests'],
            'pending_requests': request_stats['pending_requests'],
            'approved_requests': request_stats['approved_requests'],
            'used_days_ytd': balance_stats['used_days_ytd'] or 0,
            'pending_days': balance_stats['pending_days'] or 0,
        }
        
        context.update({
            'page_title': 'Leave Management',
            'active_nav': 'leave',
            'leave_balances': leave_balances,
            'pending_approvals': pending_approvals,
            'upcoming_leave': upcoming_leave,
            'stats': stats,
            'current_year': current_year,
        })
        return context


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """Create new leave request"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave_management/request_form.html'
    success_url = reverse_lazy('leave_management:overview')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = 'draft'
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'New Leave Request',
            'active_nav': 'leave',
            'leave_types': LeaveType.objects.filter(is_active=True),
        })
        return context


class LeaveRequestDetailView(LoginRequiredMixin, DetailView):
    """View leave request details"""
    model = LeaveRequest
    template_name = 'leave_management/request_detail.html'
    context_object_name = 'leave_request'
    
    def get_queryset(self):
        user = self.request.user
        if user.is_manager() or user.is_admin():
            return LeaveRequest.objects.all()
        else:
            return LeaveRequest.objects.filter(user=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'Leave Request #{self.object.request_id}',
            'active_nav': 'leave',
        })
        return context


@login_required
def submit_leave_request(request, pk):
    """Submit a draft leave request for approval"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk, user=request.user)
    
    if leave_request.status != 'draft':
        messages.error(request, 'Only draft requests can be submitted')
        return redirect('leave_management:detail', pk=pk)
    
    # Validate request
    if not leave_request.is_sufficient_notice():
        messages.error(request, 'Insufficient advance notice for this leave type')
        return redirect('leave_management:detail', pk=pk)
    
    # Check leave balance if applicable
    try:
        balance = LeaveBalance.objects.get(
            user=request.user,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year
        )
        if not balance.can_request(leave_request.get_duration_days()):
            messages.error(request, 'Insufficient leave balance')
            return redirect('leave_management:detail', pk=pk)
    except LeaveBalance.DoesNotExist:
        pass  # Balance not tracked for this leave type
    
    # Submit request
    leave_request.status = 'submitted'
    leave_request.submitted_at = timezone.now()
    leave_request.save()
    
    messages.success(request, 'Leave request submitted for approval')
    return redirect('leave_management:detail', pk=pk)


@login_required
def approve_leave_request(request, pk):
    """Approve a leave request (managers only)"""
    if not (request.user.is_manager() or request.user.is_admin()):
        messages.error(request, 'Permission denied')
        return redirect('leave_management:overview')
    
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        notes = data.get('notes', '')
        
        # Update request
        if leave_request.requires_hr_approval():
            leave_request.status = 'pending_hr'
        else:
            leave_request.status = 'approved'
        
        leave_request.manager_reviewed_at = timezone.now()
        leave_request.manager_reviewed_by = request.user
        leave_request.manager_notes = notes
        leave_request.save()
        
        # Update leave balance
        try:
            balance, created = LeaveBalance.objects.get_or_create(
                user=leave_request.user,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            balance.pending += leave_request.get_duration_days()
            balance.save()
        except Exception:
            pass  # Balance tracking optional
        
        return JsonResponse({'success': True, 'status': leave_request.status})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def decline_leave_request(request, pk):
    """Decline a leave request (managers only)"""
    if not (request.user.is_manager() or request.user.is_admin()):
        messages.error(request, 'Permission denied')
        return redirect('leave_management:overview')
    
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        leave_request.status = 'declined'
        leave_request.manager_reviewed_at = timezone.now()
        leave_request.manager_reviewed_by = request.user
        leave_request.decline_reason = reason
        leave_request.save()
        
        return JsonResponse({'success': True, 'status': leave_request.status})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def cancel_leave_request(request, pk):
    """Cancel a leave request"""
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    
    # Check permissions
    if leave_request.user != request.user and not (request.user.is_manager() or request.user.is_admin()):
        messages.error(request, 'Permission denied')
        return redirect('leave_management:overview')
    
    if not leave_request.can_be_cancelled():
        messages.error(request, 'This request cannot be cancelled')
        return redirect('leave_management:detail', pk=pk)
    
    leave_request.status = 'cancelled'
    leave_request.save()
    
    # Update leave balance if was approved
    if leave_request.status in ['approved', 'pending_hr']:
        try:
            balance = LeaveBalance.objects.get(
                user=leave_request.user,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            balance.pending -= leave_request.get_duration_days()
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass
    
    messages.success(request, 'Leave request cancelled')
    return redirect('leave_management:overview')


class LeaveCalendarView(LoginRequiredMixin, ListView):
    """Calendar view of leave requests"""
    template_name = 'leave_management/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range (current month by default)
        today = timezone.now().date()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))
        
        # Get leave requests for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        user = self.request.user
        if user.is_manager() or user.is_admin():
            leave_requests = LeaveRequest.objects.filter(
                status__in=['approved', 'pending_manager', 'pending_hr'],
                start_date__lte=end_date,
                end_date__gte=start_date
            ).select_related('user', 'leave_type')
        else:
            leave_requests = LeaveRequest.objects.filter(
                user=user,
                status__in=['approved', 'pending_manager', 'pending_hr'],
                start_date__lte=end_date,
                end_date__gte=start_date
            ).select_related('leave_type')
        
        context.update({
            'page_title': 'Leave Calendar',
            'active_nav': 'leave',
            'current_month': month,
            'current_year': year,
            'leave_requests': leave_requests,
            'calendar_data': self._build_calendar_data(leave_requests, year, month),
        })
        return context
    
    def _build_calendar_data(self, leave_requests, year, month):
        """Build calendar data structure for template"""
        import calendar
        
        cal = calendar.monthcalendar(year, month)
        calendar_data = []
        
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'day': 0, 'leave_requests': []})
                else:
                    day_date = date(year, month, day)
                    day_requests = [
                        req for req in leave_requests 
                        if req.overlaps_with_date(day_date)
                    ]
                    week_data.append({
                        'day': day,
                        'date': day_date,
                        'leave_requests': day_requests,
                        'is_today': day_date == timezone.now().date(),
                    })
            calendar_data.append(week_data)
        
        return calendar_data


@login_required
def leave_balance_api(request):
    """API endpoint for leave balance data"""
    user = request.user
    year = int(request.GET.get('year', timezone.now().year))
    
    balances = LeaveBalance.objects.filter(
        user=user,
        year=year
    ).select_related('leave_type')
    
    balance_data = []
    for balance in balances:
        balance_data.append({
            'leave_type': balance.leave_type.name,
            'color': balance.leave_type.color,
            'total_available': float(balance.total_available),
            'used': float(balance.used),
            'pending': float(balance.pending),
            'remaining': float(balance.remaining),
        })
    
    return JsonResponse({'balances': balance_data})
