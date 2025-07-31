"""
Calendar API for TPS V1.4
Provides calendar data for month and week views with users vertical, days horizontal
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Q

from apps.teams.models import Team
from apps.assignments.models import Assignment
from apps.accounts.models import User


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow unauthenticated access for development
def calendar_month(request, team_id):
    """
    Get calendar data for a specific month
    Layout: Users vertically, days horizontally
    """
    try:
        # Get parameters
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        start_date_str = request.GET.get('start_date')
        extend_to_next_month = request.GET.get('extend_to_next_month', 'false').lower() == 'true'
        
        # Validate team
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            next_month_start = date(year + 1, 1, 1)
            month_end = next_month_start - timedelta(days=1)
        else:
            next_month_start = date(year, month + 1, 1)
            month_end = next_month_start - timedelta(days=1)
        
        # If start_date is provided, use it instead of month_start
        if start_date_str:
            try:
                start_date_parsed = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                # Only use start_date if it's within the requested month
                if start_date_parsed.year == year and start_date_parsed.month == month:
                    month_start = start_date_parsed
            except ValueError:
                pass  # Invalid date format, use month_start
        
        # If extending to next month, calculate how many days to show from next month
        calendar_end = month_end
        if extend_to_next_month:
            # Show at least 30 days total from start date
            days_shown = (month_end - month_start).days + 1
            if days_shown < 30:
                additional_days = 30 - days_shown
                calendar_end = month_end + timedelta(days=additional_days)
        
        # Get all team members with waakdienst skill
        team_members = User.objects.filter(
            user_skills__skill__name="Waakdienst"
        ).distinct().order_by('first_name', 'last_name')
        
        # If no team members found, get all users for demo
        if not team_members.exists():
            team_members = User.objects.all()[:10]  # Limit for demo
        
        # Get all assignments for the extended period
        assignments = Assignment.objects.filter(
            shift__date__range=[month_start, calendar_end],
            user__in=team_members
        ).select_related('shift', 'user', 'shift__template').order_by('shift__start_datetime')
        
        # Build calendar structure
        calendar_data = {
            'month': month,
            'year': year,
            'month_name': month_start.strftime('%B'),
            'month_start': month_start.isoformat(),
            'month_end': calendar_end.isoformat(),
            'original_month_end': month_end.isoformat(),
            'team': {
                'id': team.pk,
                'name': team.name
            },
            'users': [],
            'days': []
        }
        
        # Generate days array (including next month days if extended)
        current_date = month_start
        while current_date <= calendar_end:
            calendar_data['days'].append({
                'date': current_date.isoformat(),
                'day_name': current_date.strftime('%a'),
                'day_number': current_date.day,
                'is_weekend': current_date.weekday() >= 5,
                'is_next_month': current_date > month_end
            })
            current_date += timedelta(days=1)
        
        # Build user data with their assignments
        for user in team_members:
            user_assignments = assignments.filter(user=user)
            
            # Group assignments by date
            assignments_by_date = {}
            for assignment in user_assignments:
                shift_date = assignment.shift.date.isoformat()
                if shift_date not in assignments_by_date:
                    assignments_by_date[shift_date] = []
                
                # Convert to local timezone for display
                start_local = assignment.shift.start_datetime.astimezone(timezone.get_current_timezone())
                end_local = assignment.shift.end_datetime.astimezone(timezone.get_current_timezone())
                
                assignments_by_date[shift_date].append({
                    'id': assignment.pk,
                    'start_time': start_local.strftime('%H:%M'),
                    'end_time': end_local.strftime('%H:%M'),
                    'type': assignment.shift.template.category.name if assignment.shift.template.category else 'Unknown',
                    'status': assignment.status,
                    'is_overnight': start_local.date() != end_local.date()
                })
            
            user_data = {
                'id': user.pk,
                'name': user.get_full_name(),
                'initials': f"{user.first_name[0]}{user.last_name[0]}" if user.first_name and user.last_name else user.username[:2],
                'assignments': assignments_by_date
            }
            calendar_data['users'].append(user_data)
        
        return Response(calendar_data)
        
    except Exception as e:
        return Response(
            {'error': f'Calendar data fetch failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow unauthenticated access for development
def calendar_summary(request, team_id):
    """
    Get summary statistics for calendar
    """
    try:
        # Get parameters
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        
        # Validate team
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get team members
        team_members = User.objects.filter(
            user_skills__skill__name="Waakdienst"
        ).distinct()
        
        # If no team members found, get all users for demo
        if not team_members.exists():
            team_members = User.objects.all()[:10]
        
        # Get assignments for the month
        assignments = Assignment.objects.filter(
            shift__date__range=[month_start, month_end],
            user__in=team_members
        ).select_related('shift', 'user')
        
        # Calculate statistics
        total_assignments = assignments.count()
        total_users = team_members.count()
        total_shifts = assignments.values('shift').distinct().count()
        
        # Coverage rate (assuming full coverage should be 12 shifts per week)
        total_days = (month_end - month_start).days + 1
        weeks_in_month = total_days / 7
        expected_shifts = int(weeks_in_month * 12)  # 12 shifts per week
        coverage_rate = min(100.0, (total_shifts / expected_shifts * 100)) if expected_shifts > 0 else 0
        
        summary = {
            'team': {
                'id': team.pk,
                'name': team.name
            },
            'period': {
                'month': month,
                'year': year,
                'start_date': month_start.isoformat(),
                'end_date': month_end.isoformat()
            },
            'statistics': {
                'total_team_members': total_users,
                'total_shifts': total_shifts,
                'total_assignments': total_assignments,
                'coverage_rate': round(coverage_rate, 1),
                'status': 'complete' if coverage_rate >= 95 else 'partial'
            }
        }
        
        return Response(summary)
        
    except Exception as e:
        return Response(
            {'error': f'Calendar summary fetch failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
