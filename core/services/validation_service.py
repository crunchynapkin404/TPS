"""
Validation Service for TPS V1.4
Handles all business rule validation for assignments
"""

import logging
from datetime import date, timedelta
from typing import List, Optional, Dict

from django.utils import timezone

from apps.accounts.models import User
from apps.assignments.models import Assignment
from apps.scheduling.models import ShiftInstance, ShiftTemplate
from apps.leave_management.models import LeaveRequest

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for validating assignment business rules
    """
    
    def validate_user_availability(self, user: User, assignment_date: date) -> bool:
        """
        Validate if user is available on the specified date
        Checks for leave requests and other conflicts
        """
        # Check for approved leave requests
        leave_conflicts = LeaveRequest.objects.filter(
            user=user,
            start_date__lte=assignment_date,
            end_date__gte=assignment_date,
            status='APPROVED'
        ).exists()
        
        if leave_conflicts:
            logger.debug(f"User {user.get_full_name()} has leave conflict on {assignment_date}")
            return False
        
        # Check for existing assignments on the same date
        existing_assignments = Assignment.objects.filter(
            user=user,
            shift__date=assignment_date,
            status__in=['confirmed', 'proposed']
        ).exists()
        
        if existing_assignments:
            logger.debug(f"User {user.get_full_name()} already assigned on {assignment_date}")
            return False
            
        return True
    
    def validate_required_skills(self, user: User, shift_template: ShiftTemplate) -> bool:
        """
        Validate if user has required skills for the shift template
        """
        # Get user's skills for the shift category
        category_name = shift_template.category.lower()
        
        user_skills = user.user_skills.filter(
            skill__category__name__icontains=category_name,
            proficiency_level__in=['intermediate', 'advanced', 'expert']
        )
        
        # For now, require at least one relevant skill
        # This could be enhanced to check specific skill requirements
        has_required_skills = user_skills.exists()
        
        if not has_required_skills:
            logger.debug(f"User {user.get_full_name()} lacks skills for {shift_template.category}")
            
        return has_required_skills
    
    def validate_workload_limits(self, user: User, shift_template: ShiftTemplate) -> bool:
        """
        Validate if user hasn't exceeded workload limits
        TPS rules: max 8 waakdienst weeks, max 12 incident weeks per year
        """
        if shift_template.category == 'WAAKDIENST':
            max_weeks = 8
            current_weeks = user.ytd_waakdienst_weeks or 0
        elif shift_template.category == 'INCIDENT':
            max_weeks = 12
            current_weeks = user.ytd_incident_weeks or 0
        else:
            # Other shift types have no specific limits
            return True
            
        within_limits = current_weeks < max_weeks
        
        if not within_limits:
            logger.debug(
                f"User {user.get_full_name()} has reached {shift_template.category} "
                f"limit: {current_weeks}/{max_weeks} weeks"
            )
            
        return within_limits
    
    def validate_gap_requirements(self, user: User, shift_instance: ShiftInstance) -> bool:
        """
        Validate gap requirements between assignments
        Waakdienst: 14-day gap, Incident: 7-day gap
        """
        shift_template = shift_instance.template
        assignment_date = shift_instance.date
        
        # Determine required gap
        if shift_template.category == 'WAAKDIENST':
            required_gap = 14
        elif shift_template.category == 'INCIDENT':
            required_gap = 7
        else:
            # No gap requirement for other shift types
            return True
        
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
        ).exists()
        
        if gap_violations:
            logger.debug(
                f"User {user.get_full_name()} has gap violation for {shift_template.category} "
                f"on {assignment_date} (required gap: {required_gap} days)"
            )
            
        return not gap_violations
    
    def validate_consecutive_assignments(
        self, 
        user: User, 
        shift_instance: ShiftInstance,
        max_consecutive: int = 2
    ) -> bool:
        """
        Validate that user doesn't have too many consecutive assignments
        """
        assignment_date = shift_instance.date
        shift_category = shift_instance.template.category
        
        # Check previous consecutive assignments
        consecutive_count = 0
        check_date = assignment_date - timedelta(days=7)
        
        for week_offset in range(max_consecutive):
            weekly_assignment = Assignment.objects.filter(
                user=user,
                shift__template__category__name=shift_category,
                shift__date__range=[
                    check_date - timedelta(days=3),
                    check_date + timedelta(days=3)
                ],
                status__in=['confirmed', 'proposed']
            ).exists()
            
            if weekly_assignment:
                consecutive_count += 1
                check_date -= timedelta(days=7)
            else:
                break
        
        within_limit = consecutive_count < max_consecutive
        
        if not within_limit:
            logger.debug(
                f"User {user.get_full_name()} would have {consecutive_count + 1} "
                f"consecutive {shift_category} assignments"
            )
            
        return within_limit
    
    def validate_team_coverage(
        self, 
        shift_instance: ShiftInstance,
        exclude_assignment: Optional[Assignment] = None
    ) -> bool:
        """
        Validate that shift has adequate coverage
        """
        current_assignments = Assignment.objects.filter(
            shift=shift_instance,
            status__in=['confirmed', 'proposed']
        )
        
        if exclude_assignment:
            current_assignments = current_assignments.exclude(id=exclude_assignment.id)
            
        assignment_count = current_assignments.count()
        required_staff = getattr(shift_instance, 'required_staff', 1)
        
        has_adequate_coverage = assignment_count >= required_staff
        
        if not has_adequate_coverage:
            logger.debug(
                f"Shift {shift_instance} has inadequate coverage: "
                f"{assignment_count}/{required_staff} staff"
            )
            
        return has_adequate_coverage
    
    def validate_certification_requirements(
        self, 
        user: User, 
        shift_template: ShiftTemplate
    ) -> bool:
        """
        Validate that user has required certifications for the shift
        """
        # Get skills that require certification for this shift type
        required_certified_skills = user.user_skills.filter(
            skill__category__name__icontains=shift_template.category.lower(),
            skill__requires_certification=True
        )
        
        # Check that all required certifications are valid
        for user_skill in required_certified_skills:
            if not user_skill.is_certified:
                logger.debug(
                    f"User {user.get_full_name()} lacks certification for "
                    f"{user_skill.skill.name}"
                )
                return False
                
            # Check certification expiry
            if user_skill.certification_expiry:
                if user_skill.certification_expiry < timezone.now().date():
                    logger.debug(
                        f"User {user.get_full_name()} has expired certification for "
                        f"{user_skill.skill.name}"
                    )
                    return False
                    
        return True
    
    def get_assignment_conflicts(
        self, 
        user: User, 
        shift_instance: ShiftInstance
    ) -> List[str]:
        """
        Get all validation conflicts for an assignment
        Returns list of human-readable conflict descriptions
        """
        conflicts = []
        
        if not self.validate_user_availability(user, shift_instance.date):
            conflicts.append("User not available on this date")
            
        if not self.validate_required_skills(user, shift_instance.template):
            conflicts.append("User lacks required skills")
            
        if not self.validate_workload_limits(user, shift_instance.template):
            conflicts.append("User has reached workload limits")
            
        if not self.validate_gap_requirements(user, shift_instance):
            category = shift_instance.template.category
            gap_days = 14 if category == 'WAAKDIENST' else 7
            conflicts.append(f"Violates {gap_days}-day gap requirement")
            
        if not self.validate_consecutive_assignments(user, shift_instance):
            conflicts.append("Too many consecutive assignments")
            
        if not self.validate_certification_requirements(user, shift_instance.template):
            conflicts.append("Missing required certifications")
            
        return conflicts
    
    def validate_bulk_assignments(
        self, 
        assignments: List[tuple]  # List of (user, shift_instance) tuples
    ) -> Dict[int, List[str]]:
        """
        Validate multiple assignments and return conflicts for each
        Returns dict mapping assignment index to list of conflicts
        """
        all_conflicts = {}
        
        for i, (user, shift_instance) in enumerate(assignments):
            conflicts = self.get_assignment_conflicts(user, shift_instance)
            if conflicts:
                all_conflicts[i] = conflicts
                
        return all_conflicts
