"""
TPS V1.4 - Waakdienst Planning Service
After-hours and weekend coverage planning
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


class WaakdienstPlanningService:
    """
    Waakdienst Planning Service
    
    Provides complete coverage for all non-business hours.
    One engineer covers Wednesday 17:00 to next Wednesday 08:00.
    
    Coverage pattern (12 separate shifts):
    1. Wednesday 17:00 → 24:00 (7 hours)
    2. Thursday 00:00 → 08:00 (8 hours)
    3. Thursday 17:00 → 24:00 (7 hours)
    4. Friday 00:00 → 08:00 (8 hours)
    5. Friday 17:00 → 24:00 (7 hours)
    6. Saturday 00:00 → 24:00 (24 hours)
    7. Sunday 00:00 → 24:00 (24 hours)
    8. Monday 00:00 → 08:00 (8 hours)
    9. Monday 17:00 → 24:00 (7 hours)
    10. Tuesday 00:00 → 08:00 (8 hours)
    11. Tuesday 17:00 → 24:00 (7 hours)
    12. Wednesday 00:00 → 08:00 (8 hours)
    
    Handover: Wednesday 08:00-17:00 (covered by incident planning)
    Total: 123 hours of waakdienst coverage per week
    """

    def __init__(self, team: Team):
        """Initialize waakdienst planning for a specific team"""
        self.team = team
        self.fairness_service = FairnessService(team)
        
        # Get qualified engineers
        self.qualified_engineers = self._get_qualified_engineers()
        
        logger.info(f"Initialized Waakdienst Planning for {team.name}")
        logger.info(f"Qualified engineers: {len(self.qualified_engineers)}")
    
    def _get_qualified_engineers(self, exclude_user=None):
        """Get engineers qualified for waakdienst roles"""
        from apps.accounts.models import User
        
        # Simple qualification: just need "Waakdienst" skill
        qualified_users = User.objects.filter(
            user_skills__skill__name="Waakdienst"
        ).distinct()
        
        if exclude_user:
            qualified_users = qualified_users.exclude(id=exclude_user.id)
            
        return qualified_users

    def generate_waakdienst_planning(
        self, 
        start_date: date, 
        weeks: int,
        algorithm: str = 'balanced'
    ) -> PlanningResult:
        """
        Generate waakdienst planning for the specified period
        Creates 12 individual shifts per week for complete non-business hour coverage
        """
        logger.info(f"Generating waakdienst planning: {start_date} for {weeks} weeks")
        
        assignments = []
        errors = []
        
        try:
            # Get flexible waakdienst template
            waakdienst_template = self._get_or_create_template("Waakdienst Coverage", "00:00", "23:59", Decimal('1.0'))
            
            # Generate weekly waakdienst assignments
            current_date = start_date
            for week_num in range(weeks):
                week_start = self._find_next_wednesday(current_date)
                
                # Get best engineer for this week
                best_engineer = self._find_best_waakdienst_candidate(week_start, assignments)
                
                if best_engineer:
                    # Create all waakdienst shifts for this engineer for the week
                    week_assignments = self._create_waakdienst_week_shifts(
                        best_engineer, week_start, waakdienst_template
                    )
                    assignments.extend(week_assignments)
                    
                    logger.info(f"Assigned {best_engineer.get_full_name()} to waakdienst week {week_start} ({len(week_assignments)} shifts - 123 hours)")
                else:
                    error_msg = f"No suitable engineer found for waakdienst week {week_start}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                
                current_date = week_start + timedelta(days=7)
                
        except Exception as e:
            error_msg = f"Waakdienst planning failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
        success = len(assignments) > 0 and len(errors) == 0
        
        return PlanningResult(
            success=success,
            message=f"Generated {len(assignments)} waakdienst assignments",
            data={
                'assignments': assignments,
                'total_weeks': weeks,
                'assigned_shifts': len(assignments),
                'errors': errors
            },
            errors=errors,
            status=PlanningStatus.COMPLETED if success else PlanningStatus.FAILED
        )
    
    def _find_next_wednesday(self, start_date: date) -> date:
        """Find the next Wednesday from start_date"""
        days_until_wednesday = (2 - start_date.weekday()) % 7
        if days_until_wednesday == 0 and start_date.weekday() != 2:
            days_until_wednesday = 7
        return start_date + timedelta(days=days_until_wednesday)
    
    def _create_waakdienst_week_shifts(
        self, 
        engineer: User, 
        week_start: date,
        template: ShiftTemplate
    ) -> List[Assignment]:
        """
        Create all waakdienst shifts for one engineer for one week
        
        Creates 12 shifts for complete non-business hour coverage:
        1. Wednesday 17:00 → 24:00 (7 hours) - Week start
        2. Thursday 00:00 → 08:00 (8 hours)
        3. Thursday 17:00 → 24:00 (7 hours)
        4. Friday 00:00 → 08:00 (8 hours)
        5. Friday 17:00 → 24:00 (7 hours)
        6. Saturday 00:00 → 24:00 (24 hours)
        7. Sunday 00:00 → 24:00 (24 hours)
        8. Monday 00:00 → 08:00 (8 hours)
        9. Monday 17:00 → 24:00 (7 hours)
        10. Tuesday 00:00 → 08:00 (8 hours)
        11. Tuesday 17:00 → 24:00 (7 hours)
        12. Wednesday 00:00 → 08:00 (8 hours) - Week end
        
        Total: 123 hours of coverage per week
        Handover gap: Wednesday 08:00-17:00 (covered by incident planning)
        """
        assignments = []
        
        # 1. Wednesday 17:00 → 24:00 (7 hours) - Week start
        wed_evening = self._create_shift_assignment(
            engineer, week_start, template, 
            datetime.combine(week_start, time(17, 0)),
            datetime.combine(week_start + timedelta(days=1), time(0, 0))
        )
        assignments.append(wed_evening)
        
        # 2. Thursday 00:00 → 08:00 (8 hours)
        thu_night = self._create_shift_assignment(
            engineer, week_start + timedelta(days=1), template,
            datetime.combine(week_start + timedelta(days=1), time(0, 0)),
            datetime.combine(week_start + timedelta(days=1), time(8, 0))
        )
        assignments.append(thu_night)
        
        # 3. Thursday 17:00 → 24:00 (7 hours)
        thu_evening = self._create_shift_assignment(
            engineer, week_start + timedelta(days=1), template,
            datetime.combine(week_start + timedelta(days=1), time(17, 0)),
            datetime.combine(week_start + timedelta(days=2), time(0, 0))
        )
        assignments.append(thu_evening)
        
        # 4. Friday 00:00 → 08:00 (8 hours)
        fri_night = self._create_shift_assignment(
            engineer, week_start + timedelta(days=2), template,
            datetime.combine(week_start + timedelta(days=2), time(0, 0)),
            datetime.combine(week_start + timedelta(days=2), time(8, 0))
        )
        assignments.append(fri_night)
        
        # 5. Friday 17:00 → 24:00 (7 hours)
        fri_evening = self._create_shift_assignment(
            engineer, week_start + timedelta(days=2), template,
            datetime.combine(week_start + timedelta(days=2), time(17, 0)),
            datetime.combine(week_start + timedelta(days=3), time(0, 0))
        )
        assignments.append(fri_evening)
        
        # 6. Saturday 00:00 → 24:00 (24 hours)
        sat_full = self._create_shift_assignment(
            engineer, week_start + timedelta(days=3), template,
            datetime.combine(week_start + timedelta(days=3), time(0, 0)),
            datetime.combine(week_start + timedelta(days=4), time(0, 0))
        )
        assignments.append(sat_full)
        
        # 7. Sunday 00:00 → 24:00 (24 hours)
        sun_full = self._create_shift_assignment(
            engineer, week_start + timedelta(days=4), template,
            datetime.combine(week_start + timedelta(days=4), time(0, 0)),
            datetime.combine(week_start + timedelta(days=5), time(0, 0))
        )
        assignments.append(sun_full)
        
        # 8. Monday 00:00 → 08:00 (8 hours)
        mon_night = self._create_shift_assignment(
            engineer, week_start + timedelta(days=5), template,
            datetime.combine(week_start + timedelta(days=5), time(0, 0)),
            datetime.combine(week_start + timedelta(days=5), time(8, 0))
        )
        assignments.append(mon_night)
        
        # 9. Monday 17:00 → 24:00 (7 hours)
        mon_evening = self._create_shift_assignment(
            engineer, week_start + timedelta(days=5), template,
            datetime.combine(week_start + timedelta(days=5), time(17, 0)),
            datetime.combine(week_start + timedelta(days=6), time(0, 0))
        )
        assignments.append(mon_evening)
        
        # 10. Tuesday 00:00 → 08:00 (8 hours)
        tue_night = self._create_shift_assignment(
            engineer, week_start + timedelta(days=6), template,
            datetime.combine(week_start + timedelta(days=6), time(0, 0)),
            datetime.combine(week_start + timedelta(days=6), time(8, 0))
        )
        assignments.append(tue_night)
        
        # 11. Tuesday 17:00 → 24:00 (7 hours)
        tue_evening = self._create_shift_assignment(
            engineer, week_start + timedelta(days=6), template,
            datetime.combine(week_start + timedelta(days=6), time(17, 0)),
            datetime.combine(week_start + timedelta(days=7), time(0, 0))
        )
        assignments.append(tue_evening)
        
        # 12. Wednesday 00:00 → 08:00 (8 hours) - Week end
        wed_night_end = self._create_shift_assignment(
            engineer, week_start + timedelta(days=7), template,
            datetime.combine(week_start + timedelta(days=7), time(0, 0)),
            datetime.combine(week_start + timedelta(days=7), time(8, 0))
        )
        assignments.append(wed_night_end)
        
        return assignments
    
    def _create_shift_assignment(
        self, 
        engineer: User, 
        shift_date: date, 
        template: ShiftTemplate,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Assignment:
        """Create a shift instance and assignment"""
        # Create shift instance
        shift_instance = ShiftInstance.objects.create(
            template=template,
            date=shift_date,
            start_datetime=timezone.make_aware(start_datetime) if timezone.is_naive(start_datetime) else start_datetime,
            end_datetime=timezone.make_aware(end_datetime) if timezone.is_naive(end_datetime) else end_datetime,
            status='planned'
        )
        
        # Create assignment
        assignment = Assignment.objects.create(
            shift=shift_instance,
            user=engineer,
            assignment_type='primary',
            status='confirmed',  # Auto-generated assignments are confirmed
            auto_assigned=True   # Mark as system-generated
        )
        
        return assignment
    
    def _get_or_create_template(self, name: str, start_time: str, end_time: str, duration: Decimal) -> ShiftTemplate:
        """Get or create a waakdienst shift template, always updating if exists"""
        from apps.scheduling.models import ShiftCategory
        waakdienst_cat = ShiftCategory.objects.get(name='WAAKDIENST')
        template, created = ShiftTemplate.objects.get_or_create(
            name=name,
            category=waakdienst_cat,
            defaults={
                'description': f'Waakdienst coverage: {name}',
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': duration,
                'is_overnight': start_time > end_time or (start_time == "00:00" and end_time == "00:00"),
                'is_weekly_shift': False,
                'spans_weekend': 'Weekend' in name,
                'engineers_required': 1,
                'is_active': True,
            }
        )
        # Always update to ensure correct config
        from datetime import time as dt_time
        updated = False
        
        # Convert string times to time objects for comparison
        start_time_obj = dt_time.fromisoformat(start_time) if isinstance(start_time, str) else start_time
        end_time_obj = dt_time.fromisoformat(end_time) if isinstance(end_time, str) else end_time
        
        if template.start_time != start_time_obj:
            template.start_time = start_time_obj
            updated = True
        if template.end_time != end_time_obj:
            template.end_time = end_time_obj
            updated = True
        if template.duration_hours != duration:
            template.duration_hours = duration
            updated = True
        if template.is_overnight != (start_time > end_time or (start_time == "00:00" and end_time == "00:00")):
            template.is_overnight = (start_time > end_time or (start_time == "00:00" and end_time == "00:00"))
            updated = True
        if template.spans_weekend != ('Weekend' in name):
            template.spans_weekend = ('Weekend' in name)
            updated = True
        if updated:
            template.save()
        return template
    
    def _find_best_waakdienst_candidate(
        self, 
        week_start: date, 
        existing_assignments: Optional[List[Assignment]] = None
    ) -> Optional[User]:
        """Find the best candidate for a waakdienst week using improved fairness scoring"""
        if not self.qualified_engineers:
            return None
        
        if existing_assignments is None:
            existing_assignments = []
            
        # Check who was assigned the previous week to avoid consecutive weeks
        previous_week = week_start - timedelta(weeks=1)
        previous_week_engineer = self._get_engineer_for_waakdienst_week(previous_week, existing_assignments)
        
        # Filter out the previous week's engineer
        candidates = [eng for eng in self.qualified_engineers if eng != previous_week_engineer]
        
        if not candidates:
            logger.warning("No candidates available after excluding previous week's engineer")
            candidates = self.qualified_engineers  # Use all if necessary
        
        # Calculate dynamic fairness scores
        candidate_scores = []
        current_session_weeks = self._count_waakdienst_session_weeks(existing_assignments)
        
        for engineer in candidates:
            if self._is_available_for_waakdienst(engineer, week_start):
                score = self._calculate_waakdienst_fairness_score(
                    engineer, existing_assignments, current_session_weeks
                )
                candidate_scores.append((engineer, score))
        
        if not candidate_scores:
            # If no one is perfectly available, calculate scores anyway
            for engineer in candidates:
                score = self._calculate_waakdienst_fairness_score(
                    engineer, existing_assignments, current_session_weeks
                )
                candidate_scores.append((engineer, score))
            
            logger.info("No fully available candidates, using fairness scoring anyway")
        
        # Return candidate with lowest (most fair) score
        candidate_scores.sort(key=lambda x: x[1])
        selected = candidate_scores[0][0]
        logger.debug(f"Selected {selected.get_full_name()} for waakdienst week (fairness score: {candidate_scores[0][1]:.2f})")
        return selected
    
    def _calculate_waakdienst_fairness_score(
        self, 
        engineer: User, 
        existing_assignments: List[Assignment],
        current_session_weeks: Dict[User, int]
    ) -> float:
        """
        Calculate improved fairness score for waakdienst assignments
        
        Lower score = more fair (should be assigned)
        """
        # Base score: YTD waakdienst weeks
        ytd_weeks = getattr(engineer, 'ytd_waakdienst_weeks', 0) or 0
        
        # Current session weeks (weeks assigned in this planning session)
        session_weeks = current_session_weeks.get(engineer, 0)
        
        # Total projected weeks if assigned
        total_weeks = ytd_weeks + session_weeks
        
        # Calculate team average
        all_engineers = self.qualified_engineers
        total_ytd = sum(getattr(eng, 'ytd_waakdienst_weeks', 0) or 0 for eng in all_engineers)
        total_session = sum(current_session_weeks.get(eng, 0) for eng in all_engineers)
        avg_weeks = (total_ytd + total_session) / len(all_engineers)
        
        # Primary score: deviation from average (heavily weighted)
        deviation_score = total_weeks - avg_weeks
        
        # Recency bonus: favor engineers who haven't worked recently
        weeks_since_last = self._weeks_since_last_waakdienst(engineer, existing_assignments)
        recency_bonus = min(weeks_since_last * 0.1, 1.0)  # Max bonus of 1.0
        
        # Workload balance: penalize engineers who already have many weeks this session
        session_penalty = session_weeks * 1.5  # Escalating penalty
        
        # Final score (lower is better)
        final_score = deviation_score + session_penalty - recency_bonus
        
        logger.debug(
            f"Waakdienst fairness score for {engineer.get_full_name()}: "
            f"YTD:{ytd_weeks} + Session:{session_weeks} = Total:{total_weeks} "
            f"(avg:{avg_weeks:.1f}, deviation:{deviation_score:.1f}, "
            f"session_penalty:{session_penalty:.1f}, recency_bonus:{recency_bonus:.1f}) "
            f"= {final_score:.2f}"
        )
        
        return final_score
    
    def _count_waakdienst_session_weeks(self, existing_assignments: List[Assignment]) -> Dict[User, int]:
        """Count waakdienst weeks assigned to each engineer in current planning session"""
        week_counts = {}
        engineer_weeks = {}
        
        # Count unique weeks per engineer for waakdienst assignments
        for assignment in existing_assignments:
            engineer = assignment.user
            shift_date = assignment.shift.date
            # Find Wednesday of this week (waakdienst weeks are Wednesday-based)
            week_start = shift_date - timedelta(days=(shift_date.weekday() - 2) % 7)
            
            if engineer not in engineer_weeks:
                engineer_weeks[engineer] = set()
            engineer_weeks[engineer].add(week_start)
        
        # Convert to counts
        for engineer, weeks in engineer_weeks.items():
            week_counts[engineer] = len(weeks)
        
        return week_counts
    
    def _weeks_since_last_waakdienst(
        self, 
        engineer: User, 
        existing_assignments: List[Assignment]
    ) -> int:
        """Calculate weeks since engineer's last waakdienst assignment"""
        # Find most recent waakdienst assignment for this engineer
        engineer_assignments = []
        
        # Check current session
        for assignment in existing_assignments:
            if assignment.user == engineer:
                shift_date = assignment.shift.date
                week_start = shift_date - timedelta(days=(shift_date.weekday() - 2) % 7)
                engineer_assignments.append(week_start)
        
        # Check database for recent assignments
        from apps.scheduling.models import ShiftCategory
        waakdienst_cat = ShiftCategory.objects.filter(name='WAAKDIENST').first()
        if waakdienst_cat:
            recent_db_assignments = Assignment.objects.filter(
                user=engineer,
                shift__template__category=waakdienst_cat,
                shift__date__gte=date.today() - timedelta(weeks=12)  # Last 3 months
            ).select_related('shift')
            
            for assignment in recent_db_assignments:
                shift_date = assignment.shift.date
                week_start = shift_date - timedelta(days=(shift_date.weekday() - 2) % 7)
                engineer_assignments.append(week_start)
        
        if not engineer_assignments:
            return 12  # No recent assignments, give good recency score
        
        # Find most recent week
        most_recent = max(engineer_assignments)
        current_week = date.today() - timedelta(days=(date.today().weekday() - 2) % 7)
        weeks_since = (current_week - most_recent).days // 7
        
        return max(0, weeks_since)
    
    def _get_engineer_for_waakdienst_week(
        self, 
        week_start: date, 
        existing_assignments: List[Assignment]
    ) -> Optional[User]:
        """Get the engineer assigned to waakdienst duty for a specific week"""
        # Check assignments being created in this session
        for assignment in existing_assignments:
            assignment_date = assignment.shift.date
            # Check if this assignment is in the target week (Wednesday-based)
            assignment_week = assignment_date - timedelta(days=(assignment_date.weekday() - 2) % 7)
            if assignment_week == week_start:
                return assignment.user
        
        # Check existing database assignments
        from apps.scheduling.models import ShiftCategory
        waakdienst_cat = ShiftCategory.objects.filter(name='WAAKDIENST').first()
        if waakdienst_cat:
            week_end = week_start + timedelta(days=6)  # Tuesday
            db_assignments = Assignment.objects.filter(
                shift__template__category=waakdienst_cat,
                shift__date__range=(week_start, week_end),
                status__in=['confirmed', 'proposed']
            ).first()
            
            if db_assignments:
                return db_assignments.user
                
        return None
    
    def _is_available_for_waakdienst(self, engineer: User, week_start: date) -> bool:
        """Check if engineer is available for waakdienst week"""
        week_end = week_start + timedelta(days=7)
        
        # Check for conflicts with existing assignments
        conflicts = Assignment.objects.filter(
            user=engineer,
            shift__date__range=[week_start, week_end],
            status__in=['confirmed', 'proposed']
        )
        
        return not conflicts.exists()
    
    def validate_waakdienst_prerequisites(self) -> List[str]:
        """Validate prerequisites for waakdienst planning"""
        errors = []
        
        # Check minimum team size
        if len(self.qualified_engineers) < 2:
            errors.append(f"Insufficient qualified engineers: {len(self.qualified_engineers)} (minimum 2)")
        
        # Check if waakdienst templates exist
        from apps.scheduling.models import ShiftCategory
        waakdienst_cat = ShiftCategory.objects.filter(name='WAAKDIENST').first()
        if not waakdienst_cat:
            errors.append("Waakdienst shift category not found")
        
        return errors
