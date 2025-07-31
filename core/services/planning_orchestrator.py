"""
Planning Orchestrator for TPS V1.4
Coordinates planning services to generate comprehensive team schedules
Based on V1.3.1 planning/orchestrator.py
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.teams.models import Team, TeamMembership
from apps.scheduling.models import ShiftTemplate, ShiftInstance
from apps.assignments.models import Assignment
from .waakdienst_planning_service import WaakdienstPlanningService
from .incident_planning_service import IncidentPlanningService
from .fairness_service import FairnessService
from .data_structures import (
    PlanningRequest, PlanningResult, PlanningAlgorithm, 
    ValidationResult, PlanningStatus
)

logger = logging.getLogger(__name__)


class PlanningOrchestrator:
    """
    Coordinates existing planning services to generate comprehensive team schedules.
    
    This orchestrator coordinates the waakdienst and incident planning services
    without modifying their internal logic.
    """

    def __init__(self, team: Team):
        """Initialize the orchestrator with a specific team"""
        self.team = team
        
        # Initialize the planning services
        self.waakdienst_service = WaakdienstPlanningService(team)
        self.incident_service = IncidentPlanningService(team)
        self.fairness_service = FairnessService(team)
        
        # Planning metadata for audit trails
        self.last_planning_id = None
        self.planning_history = []
        
        logger.info(f"Initialized Planning Orchestrator for {team.name}")

    def validate_prerequisites(self) -> ValidationResult:
        """
        Check all requirements before planning generation.
        Ensures data integrity and planning service readiness.
        """
        errors = []
        warnings = []
        checks = {}

        # 1. Check shift templates - more flexible validation
        # The services create templates dynamically, so we just check categories exist
        required_categories = ['INCIDENT', 'WAAKDIENST']
        
        missing_categories = []
        for category_name in required_categories:
            category_exists = ShiftTemplate.objects.filter(
                category__name=category_name,
                is_active=True
            ).exists()
            
            if not category_exists:
                missing_categories.append(category_name)
                
        if missing_categories:
            errors.append(f"Missing shift categories: {', '.join(missing_categories)}")
        checks['shift_templates'] = len(required_categories) - len(missing_categories)

        # 2. Check team
        if not self.team:
            errors.append("No team specified")
        elif not self.team.is_active:
            errors.append(f"Team '{self.team.name}' is inactive")
        checks['team'] = self.team is not None and self.team.is_active

        # 3. Check qualified engineers
        incident_engineers = self.incident_service.qualified_engineers
        waakdienst_engineers = self.waakdienst_service.qualified_engineers
        
        if not incident_engineers:
            errors.append("No engineers qualified for incident shifts")
        elif len(incident_engineers) < 2:
            warnings.append(f"Only {len(incident_engineers)} engineer(s) qualified for incident shifts")
            
        if not waakdienst_engineers:
            errors.append("No engineers qualified for waakdienst shifts")
        elif len(waakdienst_engineers) < 3:
            warnings.append(f"Only {len(waakdienst_engineers)} engineer(s) qualified for waakdienst shifts")

        checks['incident_engineers'] = len(incident_engineers)
        checks['waakdienst_engineers'] = len(waakdienst_engineers)

        # 4. Check skill-availability alignment
        team_members = self._get_team_members()
        misaligned_users = []
        
        for user in team_members:
            # Check incident skill alignment
            has_incident_skills = user.user_skills.filter(
                skill__category__name__icontains='incident'
            ).exists()
            
            # Check waakdienst skill alignment  
            has_waakdienst_skills = user.user_skills.filter(
                skill__category__name__icontains='waakdienst'
            ).exists()
            
            if not has_incident_skills and not has_waakdienst_skills:
                misaligned_users.append(f"{user.get_full_name()} (no incident or waakdienst skills)")
                
        if misaligned_users:
            warnings.extend(misaligned_users[:3])  # Show first 3
            if len(misaligned_users) > 3:
                warnings.append(f"... and {len(misaligned_users) - 3} more users without required skills")

        # 5. Check planning service readiness
        service_errors = []
        try:
            waakdienst_prereqs = self.waakdienst_service.validate_waakdienst_prerequisites()
            incident_prereqs = self.incident_service.validate_incident_prerequisites()
            
            service_errors.extend(waakdienst_prereqs)
            service_errors.extend(incident_prereqs)
            
        except Exception as e:
            service_errors.append(f"Service validation error: {str(e)}")
            
        errors.extend(service_errors)
        checks['services_ready'] = len(service_errors) == 0

        # Create result
        success = len(errors) == 0
        return ValidationResult(
            success=success,
            message="Prerequisites validation complete" if success else "Prerequisites validation failed",
            checks=checks,
            errors=errors,
            warnings=warnings
        )

    def generate_complete_planning(
        self, 
        start_date: date, 
        weeks: int, 
        algorithm: PlanningAlgorithm = PlanningAlgorithm.BALANCED
    ) -> PlanningResult:
        """
        Generate comprehensive planning for both waakdienst and incident shifts.
        This is the main entry point for creating complete schedule coverage.
        """
        logger.info(f"Starting complete planning generation: {start_date} for {weeks} weeks")
        
        # Validate prerequisites first
        validation = self.validate_prerequisites()
        if not validation.success:
            return PlanningResult(
                success=False,
                message="Prerequisites validation failed",
                data={'validation': validation.__dict__},
                errors=validation.errors,
                warnings=validation.warnings
            )

        try:
            with transaction.atomic():
                # Generate waakdienst planning
                logger.info("Generating waakdienst planning...")
                waakdienst_result = self.waakdienst_service.generate_waakdienst_planning(
                    start_date, weeks, algorithm.value
                )
                
                # Generate incident planning
                logger.info("Generating incident planning...")
                incident_result = self.incident_service.generate_incident_planning(
                    start_date, weeks, algorithm.value
                )
                
                # Combine results
                all_errors = []
                all_warnings = []
                
                if waakdienst_result.errors:
                    all_errors.extend(waakdienst_result.errors)
                if incident_result.errors:
                    all_errors.extend(incident_result.errors)
                    
                if waakdienst_result.warnings:
                    all_warnings.extend(waakdienst_result.warnings)
                if incident_result.warnings:
                    all_warnings.extend(incident_result.warnings)
                
                # Determine overall success
                overall_success = waakdienst_result.success and incident_result.success
                
                # Calculate summary statistics
                waakdienst_assignments = len(waakdienst_result.data.get('assignments', []))
                incident_assignments = len(incident_result.data.get('assignments', []))
                total_assignments = waakdienst_assignments + incident_assignments
                
                planning_result = PlanningResult(
                    success=overall_success,
                    message=f"Generated {total_assignments} total assignments " +
                           f"({waakdienst_assignments} waakdienst, {incident_assignments} incident)",
                    data={
                        'waakdienst_planning': waakdienst_result.data,
                        'incident_planning': incident_result.data,
                        'summary': {
                            'total_assignments': total_assignments,
                            'waakdienst_assignments': waakdienst_assignments,
                            'incident_assignments': incident_assignments,
                            'start_date': start_date.isoformat(),
                            'weeks': weeks,
                            'algorithm': algorithm.value
                        }
                    },
                    errors=all_errors,
                    warnings=all_warnings,
                    metadata={
                        'orchestrator': 'complete_planning',
                        'team_id': self.team.id,
                        'generated_at': timezone.now().isoformat(),
                        'waakdienst_success': waakdienst_result.success,
                        'incident_success': incident_result.success
                    }
                )
                
                # Store planning history
                self._store_planning_history(planning_result, start_date, weeks, algorithm)
                
                logger.info(f"Complete planning generation finished: {planning_result.message}")
                return planning_result
                
        except Exception as e:
            logger.error(f"Complete planning generation failed: {str(e)}")
            return PlanningResult(
                success=False,
                message=f"Planning generation failed: {str(e)}",
                data={},
                errors=[str(e)]
            )

    def preview_planning(
        self, 
        start_date: date, 
        weeks: int, 
        algorithm: PlanningAlgorithm = PlanningAlgorithm.BALANCED
    ) -> PlanningResult:
        """
        Generate a preview of planning without saving to database.
        Useful for showing users what the planning would look like.
        """
        logger.info(f"Generating planning preview: {start_date} for {weeks} weeks")
        
        # For preview, we simulate the planning without database changes
        # This would require implementing preview-only modes in the services
        
        try:
            # Validate prerequisites
            validation = self.validate_prerequisites()
            if not validation.success:
                return PlanningResult(
                    success=False,
                    message="Prerequisites validation failed",
                    data={'validation': validation.__dict__},
                    errors=validation.errors,
                    warnings=validation.warnings
                )
            
            # Calculate preview data without creating database records
            preview_data = self._calculate_preview_data(start_date, weeks, algorithm)
            
            return PlanningResult(
                success=True,
                message=f"Preview generated for {weeks} weeks",
                data={
                    'preview': True,
                    'summary': preview_data,
                    'validation': validation.__dict__
                },
                warnings=validation.warnings,
                metadata={
                    'orchestrator': 'preview_planning',
                    'team_id': self.team.id,
                    'generated_at': timezone.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Planning preview failed: {str(e)}")
            return PlanningResult(
                success=False,
                message=f"Preview generation failed: {str(e)}",
                data={},
                errors=[str(e)]
            )

    def _get_team_members(self) -> List[User]:
        """Get active team members"""
        member_ids = TeamMembership.objects.filter(
            team=self.team, is_active=True
        ).values_list('user_id', flat=True)
        
        return list(User.objects.filter(id__in=member_ids, is_active=True))

    def _calculate_preview_data(
        self, 
        start_date: date, 
        weeks: int, 
        algorithm: PlanningAlgorithm
    ) -> Dict:
        """Calculate preview data without database modifications"""
        
        # Get Wednesday-to-Wednesday periods for waakdienst
        waakdienst_weeks = self.waakdienst_service.find_wednesday_weeks(start_date, weeks)
        
        # Get business days for incident
        incident_days = self.incident_service._get_business_days(start_date, weeks)
        
        # Get qualified engineers
        waakdienst_qualified = self.waakdienst_service.qualified_engineers
        incident_qualified = self.incident_service.qualified_engineers
        
        return {
            'waakdienst_weeks': len(waakdienst_weeks),
            'incident_days': len(incident_days),
            'waakdienst_qualified_count': len(waakdienst_qualified),
            'incident_qualified_count': len(incident_qualified),
            'estimated_waakdienst_assignments': len(waakdienst_weeks),
            'estimated_incident_assignments': len(incident_days),
            'algorithm': algorithm.value,
            'period_start': start_date.isoformat(),
            'period_weeks': weeks
        }

    def _store_planning_history(
        self, 
        result: PlanningResult, 
        start_date: date, 
        weeks: int, 
        algorithm: PlanningAlgorithm
    ):
        """Store planning operation in history for audit trail"""
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'start_date': start_date.isoformat(),
            'weeks': weeks,
            'algorithm': algorithm.value,
            'success': result.success,
            'message': result.message,
            'total_assignments': result.data.get('summary', {}).get('total_assignments', 0),
            'errors_count': len(result.errors) if result.errors else 0,
            'warnings_count': len(result.warnings) if result.warnings else 0
        }
        
        self.planning_history.append(history_entry)
        
        # Keep only last 10 entries
        if len(self.planning_history) > 10:
            self.planning_history = self.planning_history[-10:]
            
    def get_planning_history(self) -> List[Dict]:
        """Get recent planning operation history"""
        return self.planning_history.copy()
    
    def get_team_workload_summary(self) -> Dict:
        """Get current team workload summary"""
        team_members = self._get_team_members()
        
        summary = {
            'team_name': self.team.name,
            'total_members': len(team_members),
            'qualified_waakdienst': len(self.waakdienst_service.qualified_engineers),
            'qualified_incident': len(self.incident_service.qualified_engineers),
            'member_workloads': []
        }
        
        for member in team_members:
            workload = {
                'user_id': member.id,
                'name': member.get_full_name(),
                'ytd_waakdienst_weeks': member.ytd_waakdienst_weeks or 0,
                'ytd_incident_weeks': member.ytd_incident_weeks or 0,
                'remaining_waakdienst': 8 - (member.ytd_waakdienst_weeks or 0),
                'remaining_incident': 12 - (member.ytd_incident_weeks or 0),
                'can_work_waakdienst': member.can_work_waakdienst(),
                'can_work_incident': member.can_work_incident()
            }
            summary['member_workloads'].append(workload)
            
        return summary
