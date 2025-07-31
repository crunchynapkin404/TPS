"""
Fairness Service for TPS V1.4
Multi-factor scoring system based on V1.3.1 enhanced_waakdienst_service.py
Implements YTD tracking, gap enforcement, and workload balancing
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Optional, Union
from django.db.models import Q, Count, QuerySet

from django.db.models import Q, Count
from django.utils import timezone

from apps.accounts.models import User
from apps.assignments.models import Assignment, SwapRequest  
from apps.scheduling.models import ShiftInstance, ShiftTemplate
from apps.leave_management.models import LeaveRequest
from apps.teams.models import Team, TeamMembership

logger = logging.getLogger(__name__)


class FairnessService:
    """
    Service for calculating fairness scores and enforcing workload balance
    Based on V1.3.1 enhanced fairness algorithms
    """
    
    def __init__(self, team: Team):
        self.team = team
        
    def calculate_fairness_score(
        self, 
        user: User, 
        shift_instance: ShiftInstance,
        period_start: date,
        period_end: date
    ) -> float:
        """
        Calculate comprehensive fairness score for user assignment
        Lower score = more fair to assign
        
        Based on V1.3.1 calculate_fairness_score algorithm
        """
        score = 0.0
        shift_template = shift_instance.template
        
        # 1. Recent assignments of same type (last 3 months)
        recent_start = period_start - timedelta(days=90)
        recent_assignments = Assignment.objects.filter(
            user=user,
            shift__template__category__name=shift_template.category.name,
            shift__date__gte=recent_start,
            status__in=['confirmed', 'proposed']
        ).count()
        score += recent_assignments * 10
        
        # 2. YTD workload balance
        if shift_template.category.name == 'WAAKDIENST':
            ytd_weeks = user.ytd_waakdienst_weeks or 0
            score += ytd_weeks * 5  # Waakdienst is weekly-based
        elif shift_template.category.name == 'INCIDENT':
            ytd_weeks = user.ytd_incident_weeks or 0
            score += ytd_weeks * 5
            
        # 3. Consecutive assignment penalty
        consecutive_penalty = self._calculate_consecutive_penalty(
            user, shift_instance, period_start
        )
        score += consecutive_penalty
        
        # 4. Gap requirement enforcement
        gap_penalty = self._calculate_gap_penalty(
            user, shift_template, shift_instance.date
        )
        score += gap_penalty
        
        # 5. Leave conflicts
        leave_penalty = self._calculate_leave_penalty(
            user, shift_instance.date, period_end
        )
        score += leave_penalty
        
        # 6. Total workload distribution
        workload_penalty = self._calculate_workload_penalty(user, shift_template)
        score += workload_penalty
        
        logger.debug(
            f"Fairness score for {user.get_full_name()} on {shift_instance.date}: {score:.2f}"
        )
        
        return score
    
    def _calculate_consecutive_penalty(
        self, 
        user: User, 
        shift_instance: ShiftInstance,
        period_start: date
    ) -> float:
        """Calculate penalty for consecutive assignments"""
        penalty = 0.0
        
        # Check previous week assignments  
        last_week = period_start - timedelta(days=7)
        previous_assignments = Assignment.objects.filter(
            user=user,
            shift__template__category__name=shift_instance.template.category.name,
            shift__date__range=[
                last_week - timedelta(days=3),
                last_week + timedelta(days=3)
            ],
            status__in=['confirmed', 'proposed']
        ).exists()
        
        if previous_assignments:
            penalty += 100  # Heavy penalty for consecutive weeks
            
        # Check next week assignments (for planning ahead)
        next_week = period_start + timedelta(days=7)
        next_assignments = Assignment.objects.filter(
            user=user,
            shift__template__category__name=shift_instance.template.category.name,
            shift__date__range=[
                next_week - timedelta(days=3),
                next_week + timedelta(days=3)
            ],
            status__in=['confirmed', 'proposed']
        ).exists()
        
        if next_assignments:
            penalty += 50  # Moderate penalty for planning consecutive
            
        return penalty
    
    def _calculate_gap_penalty(
        self, 
        user: User, 
        shift_template: ShiftTemplate,
        assignment_date: date
    ) -> float:
        """
        Calculate penalty for violating gap requirements
        Waakdienst: 14-day gap, Incident: 7-day gap
        """
        penalty = 0.0
        
        # Determine required gap
        if shift_template.category == 'WAAKDIENST':
            required_gap = 14
        elif shift_template.category == 'INCIDENT':
            required_gap = 7
        else:
            return 0.0
            
        # Check for recent assignments within gap period
        gap_start = assignment_date - timedelta(days=required_gap)
        gap_end = assignment_date + timedelta(days=required_gap)
        
        gap_violations = Assignment.objects.filter(
            user=user,
            shift__template__category__name=shift_template.category,
            shift__date__range=[gap_start, gap_end],
            status__in=['confirmed', 'proposed']
        ).exclude(
            shift__date=assignment_date  # Exclude the current assignment
        ).count()
        
        penalty += gap_violations * 200  # Heavy penalty for gap violations
        
        return penalty
    
    def _calculate_leave_penalty(
        self, 
        user: User, 
        assignment_date: date,
        period_end: date
    ) -> float:
        """Calculate penalty for leave conflicts"""
        penalty = 0.0
        
        # Check for approved leave requests
        leave_conflicts = LeaveRequest.objects.filter(
            user=user,
            start_date__lte=assignment_date,
            end_date__gte=assignment_date,
            status='APPROVED'
        ).exists()
        
        if leave_conflicts:
            penalty += 1000  # Very high penalty for leave conflicts
            
        # Check for pending leave requests
        pending_conflicts = LeaveRequest.objects.filter(
            user=user,
            start_date__lte=assignment_date,
            end_date__gte=assignment_date,
            status='pending_confirmation'
        ).exists()
        
        if pending_conflicts:
            penalty += 100  # Moderate penalty for pending leave
            
        return penalty
    
    def _calculate_workload_penalty(
        self, 
        user: User, 
        shift_template: ShiftTemplate
    ) -> float:
        """Calculate penalty based on total workload distribution"""
        penalty = 0.0
        
        # Get current year assignments for this shift type
        current_year = timezone.now().year
        year_start = date(current_year, 1, 1)
        
        user_assignments = Assignment.objects.filter(
            user=user,
            shift__template__category__name=shift_template.category,
            shift__date__gte=year_start,
            status__in=['confirmed', 'proposed']
        ).count()
        
        # Calculate team average for comparison
        team_member_ids = TeamMembership.objects.filter(
            team=self.team, is_active=True
        ).values_list('user_id', flat=True)
        
        team_users = User.objects.filter(id__in=team_member_ids, is_active=True)
        total_assignments = Assignment.objects.filter(
            user__in=team_users,
            shift__template__category__name=shift_template.category,
            shift__date__gte=year_start,
            status__in=['confirmed', 'proposed']
        ).count()
        
        if team_users.count() > 0:
            team_average = total_assignments / team_users.count()
            
            # Penalty increases with assignments above average
            if user_assignments > team_average:
                penalty += (user_assignments - team_average) * 15
                
        return penalty
    
    def get_fairness_ranking(
        self, 
        shift_instance: ShiftInstance,
        period_start: date,
        period_end: date,
        candidate_users: Optional[Union[List[User], QuerySet]] = None
    ) -> List[Dict]:
        """
        Get users ranked by fairness score for a specific shift
        Returns list of user data with scores
        """
        if candidate_users is None:
            team_member_ids = TeamMembership.objects.filter(
                team=self.team, is_active=True
            ).values_list('user_id', flat=True)
            candidate_users = list(User.objects.filter(id__in=team_member_ids, is_active=True))
            
        rankings = []
        
        for user in candidate_users:
            fairness_score = self.calculate_fairness_score(
                user, shift_instance, period_start, period_end
            )
            
            rankings.append({
                'user': user,
                'user_id': user.id,
                'name': user.get_full_name(),
                'fairness_score': fairness_score,
                'ytd_waakdienst_weeks': user.ytd_waakdienst_weeks or 0,
                'ytd_incident_weeks': user.ytd_incident_weeks or 0,
            })
            
        # Sort by fairness score (lower is better)
        rankings.sort(key=lambda x: x['fairness_score'])
        
        return rankings
    
    def validate_assignment_limits(self, user: User, shift_template: ShiftTemplate) -> List[str]:
        """
        Validate TPS business rules for assignment limits
        Returns list of violation messages
        """
        violations = []
        
        if shift_template.category == 'WAAKDIENST':
            max_weeks = 8  # TPS rule: max 8 waakdienst weeks per year
            current_weeks = user.ytd_waakdienst_weeks or 0
            
            if current_weeks >= max_weeks:
                violations.append(
                    f"User {user.get_full_name()} has reached maximum waakdienst weeks ({max_weeks})"
                )
                
        elif shift_template.category == 'INCIDENT':
            max_weeks = 12  # TPS rule: max 12 incident weeks per year  
            current_weeks = user.ytd_incident_weeks or 0
            
            if current_weeks >= max_weeks:
                violations.append(
                    f"User {user.get_full_name()} has reached maximum incident weeks ({max_weeks})"
                )
                
        return violations
