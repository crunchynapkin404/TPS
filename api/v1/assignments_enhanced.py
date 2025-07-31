"""
Enhanced Assignments API for TPS V1.4
Provides comprehensive assignment data with real-time statistics
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F
from datetime import datetime, timedelta
import json

from apps.assignments.models import Assignment
from apps.scheduling.models import ShiftInstance
from apps.teams.models import Team
from apps.accounts.models import User


@login_required
@require_http_methods(["GET"])
def assignments_overview(request):
    """Get comprehensive assignments overview with statistics"""
    try:
        # Get current date for filtering
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Get query parameters for filtering
        status_filter = request.GET.get('status', '')
        date_filter = request.GET.get('date_range', 'all')
        
        # Base queryset with proper relationships
        assignments_qs = Assignment.objects.select_related(
            'user', 
            'shift', 
            'shift__template', 
            'shift__template__category'
        )
        
        # Apply filters
        if status_filter:
            assignments_qs = assignments_qs.filter(status=status_filter)
            
        # Apply date filters
        if date_filter == 'today':
            assignments_qs = assignments_qs.filter(shift__date=today)
        elif date_filter == 'this_week':
            assignments_qs = assignments_qs.filter(shift__date__gte=week_start, shift__date__lt=week_start + timedelta(days=7))
        elif date_filter == 'this_month':
            assignments_qs = assignments_qs.filter(shift__date__gte=month_start)
        
        # Get assignments with pagination
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        offset = (page - 1) * page_size
        
        assignments = assignments_qs[offset:offset + page_size]
        total_assignments = assignments_qs.count()
        
        # Format assignments data
        assignments_data = []
        for assignment in assignments:
            # Get team info through user membership (if exists)
            user_team = assignment.user.team_memberships.first()
            
            assignment_data = {
                'id': assignment.assignment_id,
                'user': {
                    'id': assignment.user.id,
                    'name': f"{assignment.user.first_name} {assignment.user.last_name}",
                    'email': assignment.user.email,
                    'avatar_url': f"https://ui-avatars.com/api/?name={assignment.user.first_name}+{assignment.user.last_name}&background=3b82f6&color=fff"
                },
                'team': {
                    'id': user_team.team.id,
                    'name': user_team.team.name,
                } if user_team else None,
                'shift': {
                    'id': assignment.shift.shift_id,
                    'date': assignment.shift.date.strftime('%Y-%m-%d'),
                    'date_display': assignment.shift.date.strftime('%b %d, %Y'),
                    'start_time': assignment.shift.start_datetime.strftime('%H:%M') if assignment.shift.start_datetime else '',
                    'end_time': assignment.shift.end_datetime.strftime('%H:%M') if assignment.shift.end_datetime else '',
                    'duration_hours': float(assignment.shift.template.duration_hours) if assignment.shift.template else 8,
                    'category': assignment.shift.template.category.display_name if assignment.shift.template and assignment.shift.template.category else 'General',
                    'template_name': assignment.shift.template.name if assignment.shift.template else 'Standard Shift',
                },
                'status': assignment.status,
                'status_display': assignment.get_status_display() if hasattr(assignment, 'get_status_display') else assignment.status.replace('_', ' ').title(),
                'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M') if assignment.assigned_at else '',
                'updated_at': assignment.updated_at.strftime('%Y-%m-%d %H:%M') if assignment.updated_at else '',
                'is_confirmed': assignment.status == 'confirmed',
                'is_pending': assignment.status in ['pending_confirmation', 'proposed'],
                'is_urgent': assignment.shift.date == today if assignment.shift.date else False,
                'days_until_shift': (assignment.shift.date - today).days if assignment.shift.date else 0,
                'auto_assigned': assignment.auto_assigned,
                'assignment_type': assignment.assignment_type,
            }
            assignments_data.append(assignment_data)
        
        # Calculate statistics
        total_count = Assignment.objects.count()
        confirmed_count = Assignment.objects.filter(status='confirmed').count()
        pending_count = Assignment.objects.filter(status__in=['pending_confirmation', 'proposed']).count()
        today_count = Assignment.objects.filter(shift__date=today).count()
        week_count = Assignment.objects.filter(shift__date__gte=week_start, shift__date__lt=week_start + timedelta(days=7)).count()
        
        # Coverage statistics
        total_users = User.objects.filter(is_active=True).count()
        assigned_users_today = Assignment.objects.filter(shift__date=today).values('user').distinct().count()
        coverage_rate = round((assigned_users_today / total_users * 100) if total_users > 0 else 0, 1)
        
        # Category distribution
        category_stats = Assignment.objects.filter(
            shift__template__category__isnull=False
        ).values(
            'shift__template__category__display_name'
        ).annotate(
            count=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            pending=Count('id', filter=Q(status__in=['pending_confirmation', 'proposed']))
        ).order_by('-count')[:5]
        
        return JsonResponse({
            'success': True,
            'assignments': assignments_data,
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_assignments,
                'total_pages': (total_assignments + page_size - 1) // page_size,
                'has_next': offset + page_size < total_assignments,
                'has_prev': page > 1
            },
            'statistics': {
                'total_assignments': total_count,
                'confirmed_assignments': confirmed_count,
                'pending_assignments': pending_count,
                'today_assignments': today_count,
                'week_assignments': week_count,
                'coverage_rate': coverage_rate,
                'confirmation_rate': round((confirmed_count / total_count * 100) if total_count > 0 else 0, 1)
            },
            'category_distribution': list(category_stats),
            'filters_applied': {
                'status': status_filter,
                'date_range': date_filter
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'assignments': [],
            'statistics': {}
        })


@login_required
@require_http_methods(["GET"])
def assignment_calendar(request):
    """Get assignment data formatted for calendar display"""
    try:
        # Get date range from parameters
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            # Default to current month
            today = timezone.now().date()
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        # Get assignments in date range
        assignments = Assignment.objects.filter(
            shift__date__gte=start,
            shift__date__lte=end
        ).select_related('user', 'shift', 'shift__template')
        
        # Format for calendar
        calendar_events = []
        for assignment in assignments:
            user_team = assignment.user.team_memberships.first()
            
            event = {
                'id': str(assignment.assignment_id),
                'title': f"{assignment.user.first_name} {assignment.user.last_name}",
                'start': assignment.shift.date.strftime('%Y-%m-%d'),
                'className': f'assignment-{assignment.status}',
                'extendedProps': {
                    'assignment_id': str(assignment.assignment_id),
                    'user_name': f"{assignment.user.first_name} {assignment.user.last_name}",
                    'team_name': user_team.team.name if user_team else 'No Team',
                    'shift_name': assignment.shift.template.name if assignment.shift.template else 'Standard Shift',
                    'status': assignment.status,
                    'start_time': assignment.shift.start_datetime.strftime('%H:%M') if assignment.shift.start_datetime else '09:00',
                    'end_time': assignment.shift.end_datetime.strftime('%H:%M') if assignment.shift.end_datetime else '17:00',
                }
            }
            calendar_events.append(event)
        
        return JsonResponse({
            'success': True,
            'events': calendar_events,
            'date_range': {
                'start': start.strftime('%Y-%m-%d'),
                'end': end.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'events': []
        })


@login_required
@require_http_methods(["GET"])
def assignment_analytics(request):
    """Get assignment analytics and trends"""
    try:
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Status distribution
        status_dist = Assignment.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Daily assignments for the last 30 days
        thirty_days_ago = today - timedelta(days=30)
        daily_assignments = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            count = Assignment.objects.filter(shift__date=date).count()
            daily_assignments.append({
                'date': date.strftime('%Y-%m-%d'),
                'date_display': date.strftime('%b %d'),
                'count': count
            })
        
        # Category assignment distribution
        category_assignments = Assignment.objects.filter(
            shift__template__category__isnull=False
        ).values(
            'shift__template__category__display_name'
        ).annotate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            pending=Count('id', filter=Q(status__in=['pending_confirmation', 'proposed']))
        ).order_by('-total')
        
        # User workload analysis
        user_workload = Assignment.objects.filter(
            shift__date__gte=month_start
        ).values('user__first_name', 'user__last_name').annotate(
            assignment_count=Count('id'),
            confirmed_count=Count('id', filter=Q(status='confirmed'))
        ).order_by('-assignment_count')[:10]
        
        # Format user workload
        formatted_workload = []
        for user in user_workload:
            formatted_workload.append({
                'name': f"{user['user__first_name']} {user['user__last_name']}",
                'total_assignments': user['assignment_count'],
                'confirmed_assignments': user['confirmed_count'],
                'confirmation_rate': round((user['confirmed_count'] / user['assignment_count'] * 100) if user['assignment_count'] > 0 else 0, 1)
            })
        
        return JsonResponse({
            'success': True,
            'analytics': {
                'status_distribution': list(status_dist),
                'daily_trend': daily_assignments,
                'category_distribution': list(category_assignments),
                'user_workload': formatted_workload,
                'summary': {
                    'total_assignments_month': Assignment.objects.filter(shift__date__gte=month_start).count(),
                    'total_assignments_week': Assignment.objects.filter(shift__date__gte=week_start).count(),
                    'avg_daily_assignments': round(Assignment.objects.filter(shift__date__gte=thirty_days_ago).count() / 30, 1),
                    'most_active_category': category_assignments[0]['shift__template__category__display_name'] if category_assignments else 'No data',
                    'busiest_user': formatted_workload[0]['name'] if formatted_workload else 'No data'
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'analytics': {}
        })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def quick_assignment(request):
    """Create a quick assignment"""
    try:
        data = json.loads(request.body)
        
        user_id = data.get('user_id')
        shift_id = data.get('shift_id')
        assignment_type = data.get('assignment_type', 'primary')
        
        if not all([user_id, shift_id]):
            return JsonResponse({
                'success': False,
                'error': 'User ID and shift ID are required'
            })
        
        # Create assignment
        assignment = Assignment.objects.create(
            user_id=user_id,
            shift_id=shift_id,
            assignment_type=assignment_type,
            status='pending_confirmation',
            assigned_by=request.user,
            auto_assigned=False
        )
        
        return JsonResponse({
            'success': True,
            'assignment': {
                'id': str(assignment.assignment_id),
                'user_name': f"{assignment.user.first_name} {assignment.user.last_name}",
                'shift_date': assignment.shift.date.strftime('%Y-%m-%d'),
                'status': assignment.status
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def assignment_conflicts(request):
    """Get potential assignment conflicts and issues"""
    try:
        today = timezone.now().date()
        next_week = today + timedelta(days=7)
        
        # Find double assignments (same user, same date)
        double_assignments = Assignment.objects.filter(
            shift__date__gte=today,
            shift__date__lte=next_week
        ).values('user', 'shift__date').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        conflicts = []
        for conflict in double_assignments:
            assignments = Assignment.objects.filter(
                user=conflict['user'],
                shift__date=conflict['shift__date']
            ).select_related('user', 'shift', 'shift__template')
            
            user = assignments.first().user
            user_team = user.team_memberships.first()
            
            conflicts.append({
                'type': 'double_assignment',
                'user_name': f"{user.first_name} {user.last_name}",
                'date': conflict['shift__date'].strftime('%Y-%m-%d'),
                'assignment_count': conflict['count'],
                'assignments': [
                    {
                        'id': str(a.assignment_id),
                        'team': user_team.team.name if user_team else 'No Team',
                        'shift_name': a.shift.template.name if a.shift.template else 'Standard Shift',
                        'status': a.status
                    } for a in assignments
                ]
            })
        
        # Find low coverage shifts (basic logic)
        understaffed = []
        shift_instances = ShiftInstance.objects.filter(
            date__gte=today,
            date__lte=next_week,
            status='planned'
        )
        
        for shift in shift_instances:
            assignment_count = Assignment.objects.filter(
                shift=shift,
                status__in=['confirmed', 'pending_confirmation', 'proposed']
            ).count()
            
            # Assume minimum 1 person per shift (can be configured)
            required_staff = 1  # This could be based on shift template requirements
            if assignment_count < required_staff:
                understaffed.append({
                    'type': 'understaffed',
                    'shift_name': shift.template.name if shift.template else 'Standard Shift',
                    'date': shift.date.strftime('%Y-%m-%d'),
                    'current_staff': assignment_count,
                    'required_staff': required_staff,
                    'shortfall': required_staff - assignment_count
                })
        
        return JsonResponse({
            'success': True,
            'conflicts': {
                'double_assignments': conflicts,
                'understaffed_shifts': understaffed,
                'total_issues': len(conflicts) + len(understaffed)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'conflicts': {}
        })
