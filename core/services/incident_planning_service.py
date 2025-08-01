"""
TPS V1.4 - Incident Planning Service  
Business hours incident response planning
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.teams.models import Team, TeamMembership
from apps.accounts.models import User
from apps.scheduling.models import ShiftTemplate, ShiftInstance
from apps.assignments.models import Assignment

from .data_structures import PlanningResult, PlanningStatus
from .fairness_service import FairnessService

logger = logging.getLogger(__name__)


class IncidentPlanningService:
    """
    Incident Planning Service
    
    Covers business hours (8:00-17:00) Monday-Friday:
    - Monday 8:00 - 17:00
    - Tuesday 8:00 - 17:00  
    - Wednesday 8:00 - 17:00 (includes waakdienst handover coverage)
    - Thursday 8:00 - 17:00
    - Friday 8:00 - 17:00
    
    Optional: Standby engineer for same times
    """

    def __init__(self, team: Team):
        """Initialize incident planning for a specific team"""
        self.team = team
        self.fairness_service = FairnessService(team)
        
        # Business hours configuration
        self.business_start_time = time(8, 0)   # 8:00 AM
        self.business_end_time = time(17, 0)    # 5:00 PM
        self.hours_per_day = 9  # 8:00-17:00
        
        # Get qualified engineers
        self.qualified_engineers = self._get_qualified_engineers()
        
        logger.info(f"Initialized Incident Planning for {team.name}")
        logger.info(f"Qualified engineers: {len(self.qualified_engineers)}")
    
    def _get_qualified_engineers(self, exclude_user=None):
        """Get engineers qualified for incident response roles"""
        from apps.accounts.models import User
        
        # Simple qualification: just need "Incident" skill
        qualified_users = User.objects.filter(
            user_skills__skill__name="Incident"
        ).distinct()
        
        if exclude_user:
            qualified_users = qualified_users.exclude(id=exclude_user.id)
            
        return qualified_users

    def generate_incident_planning(
        self,
        start_date: date,
        weeks: int,
        algorithm: str = 'balanced',
        include_standby: bool = False
    ) -> PlanningResult:
        """
        Generate incident planning for business days in the specified period
        
        Business Rule: Same engineer for entire week (Mon-Fri), different engineer each week
        
        Args:
            start_date: Start date for planning
            weeks: Number of weeks to plan
            algorithm: Planning algorithm to use
            include_standby: Whether to assign standby engineers
        """
        logger.info(f"Generating incident planning: {start_date} for {weeks} weeks (standby: {include_standby})")
        
        assignments = []
        errors = []
        
        try:
            # Get incident templates
            primary_template = self._get_or_create_template("Incident Primary", "08:00", "17:00", Decimal('9.0'))
            standby_template = None
            if include_standby:
                standby_template = self._get_or_create_template("Incident Standby", "08:00", "17:00", Decimal('9.0'))
            
            # Generate week-based assignments
            for week_num in range(weeks):
                week_start = start_date + timedelta(weeks=week_num)
                
                # Find Monday of this week
                monday = week_start - timedelta(days=week_start.weekday())
                
                # Select primary engineer for the entire week
                primary_engineer = self._find_best_weekly_incident_candidate(monday, assignments)
                
                if not primary_engineer:
                    error_msg = f"No suitable engineer found for incident week starting {monday}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Assign primary engineer for Monday-Friday
                week_assignments = self._create_weekly_assignments(
                    primary_engineer, monday, primary_template, 'primary'
                )
                assignments.extend(week_assignments)
                
                logger.info(f"Assigned {primary_engineer.get_full_name()} to incident primary for week {monday.strftime('%Y-%m-%d')}")
                
                # Assign standby engineer for the week if requested
                if include_standby and standby_template:
                    standby_engineer = self._find_best_weekly_incident_candidate(
                        monday, assignments, exclude_user=primary_engineer
                    )
                    
                    if standby_engineer:
                        standby_assignments = self._create_weekly_assignments(
                            standby_engineer, monday, standby_template, 'standby'
                        )
                        assignments.extend(standby_assignments)
                        logger.info(f"Assigned {standby_engineer.get_full_name()} to incident standby for week {monday.strftime('%Y-%m-%d')}")
                
        except Exception as e:
            error_msg = f"Incident planning failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
        success = len(assignments) > 0 and len(errors) == 0
        
        return PlanningResult(
            success=success,
            message=f"Generated {len(assignments)} incident assignments",
            data={
                'assignments': assignments,
                'primary_assignments': len([a for a in assignments if a.assignment_type == 'primary']),
                'standby_assignments': len([a for a in assignments if a.assignment_type == 'standby']),
                'business_days_covered': len(set(a.shift.date for a in assignments)),
                'errors': errors
            },
            errors=errors,
            status=PlanningStatus.COMPLETED if success else PlanningStatus.FAILED
        )
    
    def _create_incident_assignment(
        self, 
        engineer: User, 
        shift_date: date, 
        template: ShiftTemplate,
        assignment_type: str = 'primary'
    ) -> Assignment:
        """Create an incident shift instance and assignment"""
        # Create shift instance
        shift_instance = ShiftInstance.objects.create(
            template=template,
            date=shift_date,
            start_datetime=timezone.make_aware(
                datetime.combine(shift_date, self.business_start_time)
            ),
            end_datetime=timezone.make_aware(
                datetime.combine(shift_date, self.business_end_time)
            ),
            status='planned'
        )
        
        # Create assignment
        assignment = Assignment.objects.create(
            shift=shift_instance,
            user=engineer,
            assignment_type=assignment_type,
            status='confirmed',  # Auto-generated assignments are confirmed
            auto_assigned=True   # Mark as system-generated
        )
        
        return assignment
    
    def _get_or_create_template(self, name: str, start_time: str, end_time: str, duration: Decimal) -> ShiftTemplate:
        """Get or create an incident shift template"""
        from apps.scheduling.models import ShiftCategory
        
        incident_cat = ShiftCategory.objects.get(name='INCIDENT')
        
        template, created = ShiftTemplate.objects.get_or_create(
            name=name,
            category=incident_cat,
            defaults={
                'description': f'Incident response: {name}',
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': duration,
                'is_overnight': False,
                'is_weekly_shift': False,
                'spans_weekend': False,
                'engineers_required': 1,
                'is_active': True,
            }
        )
        
        return template
    
    def _find_best_weekly_incident_candidate(
        self, 
        week_start_monday: date, 
        existing_assignments: List[Assignment],
        exclude_user: Optional[User] = None
    ) -> Optional[User]:
        """
        Find the best candidate for a week of incident shifts using improved fairness scoring
        
        Business rule: Different engineer each week, fair rotation with dynamic balancing
        """
        if not self.qualified_engineers:
            return None
            
        # Filter out excluded user
        candidates = [eng for eng in self.qualified_engineers if eng != exclude_user]
        
        if not candidates:
            return None
        
        # Check who was assigned the previous week to avoid consecutive weeks
        previous_week_monday = week_start_monday - timedelta(weeks=1)
        previous_week_engineer = self._get_engineer_for_week(previous_week_monday, existing_assignments)
        
        # Filter out the previous week's engineer
        if previous_week_engineer:
            candidates = [eng for eng in candidates if eng != previous_week_engineer]
            logger.debug(f"Excluding {previous_week_engineer.get_full_name()} (worked previous week)")
        
        if not candidates:
            logger.warning("No candidates available after excluding previous week's engineer")
            return None
        
        # Calculate dynamic fairness scores
        candidate_scores = []
        current_session_weeks = self._count_session_weeks(existing_assignments)
        
        for engineer in candidates:
            if self._is_available_for_week(engineer, week_start_monday, existing_assignments):
                score = self._calculate_dynamic_fairness_score(
                    engineer, existing_assignments, current_session_weeks
                )
                candidate_scores.append((engineer, score))
        
        if not candidate_scores:
            # If no one is perfectly available, calculate scores anyway
            for engineer in candidates:
                score = self._calculate_dynamic_fairness_score(
                    engineer, existing_assignments, current_session_weeks
                )
                candidate_scores.append((engineer, score))
            
            logger.info("No fully available candidates, using fairness scoring anyway")
        
        # Return candidate with lowest (most fair) score
        candidate_scores.sort(key=lambda x: x[1])
        selected = candidate_scores[0][0]
        logger.debug(f"Selected {selected.get_full_name()} for incident week (fairness score: {candidate_scores[0][1]:.2f})")
        return selected
    
    def _calculate_dynamic_fairness_score(
        self, 
        engineer: User, 
        existing_assignments: List[Assignment],
        current_session_weeks: Dict[User, int]
    ) -> float:
        """
        Calculate improved fairness score considering multiple factors
        
        Lower score = more fair (should be assigned)
        """
        # Base score: YTD incident weeks
        ytd_weeks = engineer.ytd_incident_weeks
        
        # Current session weeks (weeks assigned in this planning session)
        session_weeks = current_session_weeks.get(engineer, 0)
        
        # Total projected weeks if assigned
        total_weeks = ytd_weeks + session_weeks
        
        # Calculate team average
        all_engineers = self.qualified_engineers
        total_ytd = sum(eng.ytd_incident_weeks for eng in all_engineers)
        total_session = sum(current_session_weeks.get(eng, 0) for eng in all_engineers)
        avg_weeks = (total_ytd + total_session) / len(all_engineers)
        
        # Primary score: deviation from average (heavily weighted)
        deviation_score = total_weeks - avg_weeks
        
        # Recency penalty: avoid assigning same engineer too frequently
        weeks_since_last = self._weeks_since_last_assignment(engineer, existing_assignments)
        recency_bonus = min(weeks_since_last * 0.1, 1.0)  # Max bonus of 1.0
        
        # Workload balance: penalize engineers who already have many weeks this session
        session_penalty = session_weeks * 1.5  # Escalating penalty
        
        # Final score (lower is better)
        final_score = deviation_score + session_penalty - recency_bonus
        
        logger.debug(
            f"Fairness score for {engineer.get_full_name()}: "
            f"YTD:{ytd_weeks} + Session:{session_weeks} = Total:{total_weeks} "
            f"(avg:{avg_weeks:.1f}, deviation:{deviation_score:.1f}, "
            f"session_penalty:{session_penalty:.1f}, recency_bonus:{recency_bonus:.1f}) "
            f"= {final_score:.2f}"
        )
        
        return final_score
    
    def _count_session_weeks(self, existing_assignments: List[Assignment]) -> Dict[User, int]:
        """Count weeks assigned to each engineer in current planning session"""
        week_counts = {}
        engineer_weeks = {}
        
        # Count unique weeks per engineer
        for assignment in existing_assignments:
            if assignment.assignment_type == 'primary':
                engineer = assignment.user
                shift_date = assignment.shift.date
                week_monday = shift_date - timedelta(days=shift_date.weekday())
                
                if engineer not in engineer_weeks:
                    engineer_weeks[engineer] = set()
                engineer_weeks[engineer].add(week_monday)
        
        # Convert to counts
        for engineer, weeks in engineer_weeks.items():
            week_counts[engineer] = len(weeks)
        
        return week_counts
    
    def _weeks_since_last_assignment(
        self, 
        engineer: User, 
        existing_assignments: List[Assignment]
    ) -> int:
        """Calculate weeks since engineer's last assignment (in this session or DB)"""
        # Find most recent assignment for this engineer
        engineer_assignments = []
        
        # Check current session
        for assignment in existing_assignments:
            if (assignment.user == engineer and 
                assignment.assignment_type == 'primary'):
                shift_date = assignment.shift.date
                week_monday = shift_date - timedelta(days=shift_date.weekday())
                engineer_assignments.append(week_monday)
        
        # Check database for recent assignments
        recent_db_assignments = Assignment.objects.filter(
            user=engineer,
            assignment_type='primary',
            shift__date__gte=date.today() - timedelta(weeks=12)  # Last 3 months
        ).select_related('shift')
        
        for assignment in recent_db_assignments:
            shift_date = assignment.shift.date
            week_monday = shift_date - timedelta(days=shift_date.weekday())
            engineer_assignments.append(week_monday)
        
        if not engineer_assignments:
            return 12  # No recent assignments, give good recency score
        
        # Find most recent week
        most_recent = max(engineer_assignments)
        current_monday = date.today() - timedelta(days=date.today().weekday())
        weeks_since = (current_monday - most_recent).days // 7
        
        return max(0, weeks_since)
    
    def _create_weekly_assignments(
        self, 
        engineer: User, 
        monday: date, 
        template: ShiftTemplate,
        assignment_type: str = 'primary'
    ) -> List[Assignment]:
        """Create assignments for Monday-Friday of a week"""
        assignments = []
        
        for day_offset in range(5):  # Monday (0) through Friday (4)
            shift_date = monday + timedelta(days=day_offset)
            
            assignment = self._create_incident_assignment(
                engineer, shift_date, template, assignment_type
            )
            assignments.append(assignment)
        
        return assignments
    
    def _get_engineer_for_week(
        self, 
        week_start_monday: date, 
        existing_assignments: List[Assignment]
    ) -> Optional[User]:
        """Get the engineer assigned to incident duty for a specific week"""
        # Check assignments being created in this session
        for assignment in existing_assignments:
            assignment_date = assignment.shift.date
            # Check if this assignment is in the target week
            assignment_monday = assignment_date - timedelta(days=assignment_date.weekday())
            if (assignment_monday == week_start_monday and 
                assignment.assignment_type == 'primary'):
                return assignment.user
        
        # Check existing database assignments
        week_end = week_start_monday + timedelta(days=4)  # Friday
        db_assignments = Assignment.objects.filter(
            shift__date__range=(week_start_monday, week_end),
            assignment_type='primary',
            status__in=['confirmed', 'proposed']
        ).first()
        
        if db_assignments:
            return db_assignments.user
            
        return None
    
    def _is_available_for_week(
        self, 
        engineer: User, 
        week_start_monday: date,
        existing_assignments: List[Assignment]
    ) -> bool:
        """Check if engineer is available for the entire week (Monday-Friday)"""
        # Check each day of the week
        for day_offset in range(5):  # Monday through Friday
            shift_date = week_start_monday + timedelta(days=day_offset)
            
            if not self._is_available_for_incident(engineer, shift_date, existing_assignments):
                return False
        
        return True

    def _find_best_incident_candidate(
        self, 
        shift_date: date, 
        existing_assignments: List[Assignment],
        exclude_user: Optional[User] = None
    ) -> Optional[User]:
        """Find the best candidate for an incident shift using fairness scoring"""
        if not self.qualified_engineers:
            return None
            
        # Filter out excluded user
        candidates = [eng for eng in self.qualified_engineers if eng != exclude_user]
        
        if not candidates:
            return None
        
        # Calculate fairness scores for available candidates
        candidate_scores = []
        for engineer in candidates:
            if self._is_available_for_incident(engineer, shift_date, existing_assignments):
                # Simple fairness: use YTD incident weeks (lower is more fair)
                score = engineer.ytd_incident_weeks
                candidate_scores.append((engineer, score))
        
        if not candidate_scores:
            # If no one is perfectly available, return the most fair candidate
            return min(candidates, key=lambda u: u.ytd_incident_weeks)
        
        # Return candidate with lowest (most fair) score
        candidate_scores.sort(key=lambda x: x[1])
        return candidate_scores[0][0]
    
    def _is_available_for_incident(
        self, 
        engineer: User, 
        shift_date: date,
        existing_assignments: List[Assignment]
    ) -> bool:
        """Check if engineer is available for incident shift"""
        # Check for conflicts with existing assignments in database
        db_conflicts = Assignment.objects.filter(
            user=engineer,
            shift__date=shift_date,
            status__in=['confirmed', 'proposed']
        )
        
        if db_conflicts.exists():
            return False
        
        # Check for conflicts with assignments being created in this planning session
        for assignment in existing_assignments:
            if (assignment.user == engineer and 
                assignment.shift.date == shift_date):
                return False
        
        # Check for leave requests
        from apps.leave_management.models import LeaveRequest
        leave_conflicts = LeaveRequest.objects.filter(
            user=engineer,
            start_date__lte=shift_date,
            end_date__gte=shift_date,
            status='approved'
        )
        
        return not leave_conflicts.exists()
    
    def validate_incident_prerequisites(self) -> List[str]:
        """Validate prerequisites for incident planning"""
        errors = []
        
        # Check minimum team size
        if len(self.qualified_engineers) < 1:
            errors.append(f"Insufficient qualified engineers: {len(self.qualified_engineers)} (minimum 1)")
        
        # Check if incident templates exist
        from apps.scheduling.models import ShiftCategory
        incident_cat = ShiftCategory.objects.filter(name='INCIDENT').first()
        if not incident_cat:
            errors.append("Incident shift category not found")
        
        return errors
    
    def generate_planning(self, start_date, end_date, planning_period):
        """
        Generate planning for the specified date range - wrapper for incident planning
        
        Args:
            start_date: Start date for planning
            end_date: End date for planning 
            planning_period: Planning period instance
            
        Returns:
            List of Assignment objects
        """
        # Calculate number of weeks
        delta = end_date - start_date
        weeks = max(1, (delta.days + 6) // 7)  # Round up to nearest week
        
        # Generate incident planning
        result = self.generate_incident_planning(
            start_date=start_date,
            weeks=weeks,
            algorithm='balanced',
            include_standby=False
        )
        
        # Convert result to assignment list (simplified for now)
        # The actual incident planning service returns a complex result structure
        # For now, return empty list - the fallback logic will handle it
        return []
