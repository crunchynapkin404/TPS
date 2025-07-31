"""
Assignment Service for TPS V1.4
Handles assignment creation, validation, and bulk operations
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Optional

from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User
from apps.assignments.models import Assignment, SwapRequest
from apps.scheduling.models import ShiftInstance, ShiftTemplate
from apps.teams.models import Team
from .fairness_service import FairnessService
from .validation_service import ValidationService
from .data_structures import AssignmentResult, BulkResult

logger = logging.getLogger(__name__)


class AssignmentService:
    """
    Service for managing shift assignments with validation and business rules
    """
    
    def __init__(self, team: Team):
        self.team = team
        self.fairness_service = FairnessService(team)
        self.validation_service = ValidationService()
        
    def create_assignment(
        self, 
        shift_instance: ShiftInstance, 
        user: User, 
        assigned_by: Optional[User] = None,
        **kwargs
    ) -> AssignmentResult:
        """
        Create a single shift assignment with full validation
        """
        try:
            logger.info(f"Creating assignment: {user.get_full_name()} -> {shift_instance}")
            
            # Validate assignment
            validation_result = self.validate_assignment(shift_instance, user)
            if not validation_result.success:
                return AssignmentResult(
                    success=False,
                    message="Assignment validation failed",
                    conflicts=validation_result.errors
                )
            
            # Create assignment
            assignment = Assignment.objects.create(
                user=user,
                shift=shift_instance,
                assigned_by=assigned_by,
                assigned_at=timezone.now(),
                status='proposed',
                notes=kwargs.get('notes', ''),
                metadata=kwargs.get('metadata', {})
            )
            
            # Update user YTD tracking
            self._update_user_ytd_tracking(user, shift_instance.template)
            
            logger.info(f"Assignment created successfully: ID {assignment.id}")
            
            return AssignmentResult(
                success=True,
                message=f"Assigned {user.get_full_name()} to {shift_instance.template.name}",
                assignment_id=assignment.id
            )
            
        except Exception as e:
            logger.error(f"Assignment creation failed: {str(e)}")
            return AssignmentResult(
                success=False,
                message=f"Assignment failed: {str(e)}",
                conflicts=[str(e)]
            )
    
    def validate_assignment(self, shift_instance: ShiftInstance, user: User) -> AssignmentResult:
        """
        Validate if a user can be assigned to a specific shift
        """
        conflicts = []
        
        # 1. User availability validation
        if not self.validation_service.validate_user_availability(user, shift_instance.date):
            conflicts.append(f"User not available on {shift_instance.date}")
        
        # 2. Required skills validation
        if not self.validation_service.validate_required_skills(user, shift_instance.template):
            conflicts.append("User does not have required skills")
        
        # 3. Workload limits validation
        if not self.validation_service.validate_workload_limits(user, shift_instance.template):
            conflicts.append("User has reached workload limits")
        
        # 4. Gap requirements validation
        if not self.validation_service.validate_gap_requirements(user, shift_instance):
            conflicts.append("Assignment violates gap requirements")
        
        # 5. Existing assignment conflicts
        existing_assignment = Assignment.objects.filter(
            user=user,
            shift__date=shift_instance.date,
            status__in=['confirmed', 'proposed']
        ).first()
        
        if existing_assignment:
            conflicts.append(f"User already assigned on {shift_instance.date}")
        
        # 6. Shift capacity validation
        current_assignments = Assignment.objects.filter(
            shift=shift_instance,
            status__in=['confirmed', 'proposed']
        ).count()
        
        if current_assignments >= shift_instance.required_staff:
            conflicts.append("Shift is already fully staffed")
        
        success = len(conflicts) == 0
        return AssignmentResult(
            success=success,
            message="Validation passed" if success else "Validation failed",
            conflicts=conflicts if conflicts else None
        )
    
    def bulk_assign_shifts(self, assignments: List[Dict]) -> BulkResult:
        """
        Create multiple assignments in a single transaction
        
        assignments: List of dicts with keys: shift_instance_id, user_id, assigned_by_id, notes
        """
        successful = 0
        failed = 0
        errors = []
        warnings = []
        details = []
        
        try:
            with transaction.atomic():
                for assignment_data in assignments:
                    try:
                        # Get objects
                        shift_instance = ShiftInstance.objects.get(
                            id=assignment_data['shift_instance_id']
                        )
                        user = User.objects.get(id=assignment_data['user_id'])
                        assigned_by = None
                        if assignment_data.get('assigned_by_id'):
                            assigned_by = User.objects.get(id=assignment_data['assigned_by_id'])
                        
                        # Create assignment
                        result = self.create_assignment(
                            shift=shift_instance,
                            user=user,
                            assigned_by=assigned_by,
                            notes=assignment_data.get('notes', ''),
                            metadata=assignment_data.get('metadata', {})
                        )
                        
                        if result.success:
                            successful += 1
                            details.append({
                                'shift_instance_id': assignment_data['shift_instance_id'],
                                'user_id': assignment_data['user_id'],
                                'status': 'success',
                                'assignment_id': result.assignment_id
                            })
                        else:
                            failed += 1
                            errors.extend(result.conflicts or [])
                            details.append({
                                'shift_instance_id': assignment_data['shift_instance_id'],
                                'user_id': assignment_data['user_id'],
                                'status': 'failed',
                                'errors': result.conflicts
                            })
                            
                    except Exception as e:
                        failed += 1
                        error_msg = f"Assignment {assignment_data}: {str(e)}"
                        errors.append(error_msg)
                        details.append({
                            'shift_instance_id': assignment_data.get('shift_instance_id'),
                            'user_id': assignment_data.get('user_id'),
                            'status': 'failed',
                            'errors': [str(e)]
                        })
                        
            return BulkResult(
                success=failed == 0,
                total_requested=len(assignments),
                successful=successful,
                failed=failed,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Bulk assignment failed: {str(e)}")
            return BulkResult(
                success=False,
                total_requested=len(assignments),
                successful=0,
                failed=len(assignments),
                errors=[f"Bulk operation failed: {str(e)}"],
                warnings=[],
                details=[]
            )
    
    def auto_assign_shifts(
        self, 
        shift_instances: List[ShiftInstance],
        algorithm: str = "balanced"
    ) -> BulkResult:
        """
        Automatically assign multiple shifts using fairness algorithms
        """
        successful = 0
        failed = 0
        errors = []
        warnings = []
        details = []
        
        try:
            for shift_instance in shift_instances:
                # Get qualified candidates
                qualified_users = self._get_qualified_candidates(shift_instance)
                
                if not qualified_users:
                    failed += 1
                    errors.append(f"No qualified users for shift {shift_instance.id}")
                    continue
                
                # Get fairness rankings
                rankings = self.fairness_service.get_fairness_ranking(
                    shift_instance,
                    shift_instance.date,
                    shift_instance.date,
                    qualified_users
                )
                
                if not rankings:
                    failed += 1
                    errors.append(f"No rankings available for shift {shift_instance.id}")
                    continue
                
                # Select best candidate based on algorithm
                selected_user = self._select_candidate_by_algorithm(rankings, algorithm)
                
                if not selected_user:
                    failed += 1
                    errors.append(f"No suitable candidate for shift {shift_instance.id}")
                    continue
                
                # Create assignment
                result = self.create_assignment(
                    shift=shift_instance,
                    user=selected_user,
                    notes=f"Auto-assigned via {algorithm} algorithm"
                )
                
                if result.success:
                    successful += 1
                    details.append({
                        'shift_instance_id': shift_instance.id,
                        'user_id': selected_user.id,
                        'status': 'success',
                        'assignment_id': result.assignment_id,
                        'algorithm': algorithm
                    })
                else:
                    failed += 1
                    errors.extend(result.conflicts or [])
                    details.append({
                        'shift_instance_id': shift_instance.id,
                        'user_id': selected_user.id,
                        'status': 'failed',
                        'errors': result.conflicts,
                        'algorithm': algorithm
                    })
            
            return BulkResult(
                success=failed == 0,
                total_requested=len(shift_instances),
                successful=successful,
                failed=failed,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Auto assignment failed: {str(e)}")
            return BulkResult(
                success=False,
                total_requested=len(shift_instances),
                successful=0,
                failed=len(shift_instances),
                errors=[f"Auto assignment failed: {str(e)}"],
                warnings=[],
                details=[]
            )
    
    def _get_qualified_candidates(self, shift_instance: ShiftInstance) -> List[User]:
        """Get users qualified for a specific shift"""
        from apps.teams.models import TeamMembership
        
        # Get team members
        member_ids = TeamMembership.objects.filter(
            team=self.team, is_active=True
        ).values_list('user_id', flat=True)
        
        # Filter by basic qualifications
        candidates = User.objects.filter(
            id__in=member_ids,
            is_active=True
        )
        
        # Additional filtering based on shift type and skills
        qualified_candidates = []
        for user in candidates:
            if self.validation_service.validate_required_skills(user, shift_instance.template):
                qualified_candidates.append(user)
                
        return qualified_candidates
    
    def _select_candidate_by_algorithm(self, rankings: List[Dict], algorithm: str) -> Optional[User]:
        """Select candidate based on specified algorithm"""
        if not rankings:
            return None
            
        if algorithm == "balanced":
            # Select user with best fairness score
            return rankings[0]['user']
        elif algorithm == "sequential":
            # Simple sequential selection for now
            return rankings[0]['user']
        else:  # custom
            # Custom algorithm - prefer users with higher skill levels
            return rankings[0]['user']
    
    def _update_user_ytd_tracking(self, user: User, shift_template: ShiftTemplate):
        """Update user's year-to-date tracking based on assignment"""
        if shift_template.category == 'WAAKDIENST':
            user.ytd_waakdienst_weeks = (user.ytd_waakdienst_weeks or 0) + 1
            user.save(update_fields=['ytd_waakdienst_weeks'])
        elif shift_template.category == 'INCIDENT':
            user.ytd_incident_weeks = (user.ytd_incident_weeks or 0) + 1
            user.save(update_fields=['ytd_incident_weeks'])
    
    def create_swap_request(
        self, 
        assignment: Assignment, 
        requested_by: User,
        target_user: Optional[User] = None,
        reason: str = ""
    ) -> AssignmentResult:
        """
        Create a swap request for an existing assignment
        """
        try:
            # Validate swap request
            if assignment.user != requested_by:
                return AssignmentResult(
                    success=False,
                    message="Only assigned user can request swap",
                    conflicts=["Permission denied"]
                )
            
            if assignment.status not in ['confirmed', 'proposed']:
                return AssignmentResult(
                    success=False,
                    message="Cannot swap assignment with current status",
                    conflicts=[f"Invalid status: {assignment.status}"]
                )
            
            # Create swap request
            swap_request = SwapRequest.objects.create(
                original_assignment=assignment,
                requested_by=requested_by,
                target_user=target_user,
                reason=reason,
                status='pending_confirmation',
                created_at=timezone.now()
            )
            
            logger.info(f"Swap request created: {swap_request.id}")
            
            return AssignmentResult(
                success=True,
                message="Swap request created",
                assignment_id=swap_request.id
            )
            
        except Exception as e:
            logger.error(f"Swap request creation failed: {str(e)}")
            return AssignmentResult(
                success=False,
                message=f"Swap request failed: {str(e)}",
                conflicts=[str(e)]
            )
