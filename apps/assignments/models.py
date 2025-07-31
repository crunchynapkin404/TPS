"""
TPS V1.4 - Assignment Models
Shift assignments, swaps, and audit trails
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Assignment(models.Model):
    """
    User assignments to shift instances with status tracking
    """
    STATUS_CHOICES = [
        ('proposed', 'Proposed'),
        ('pending_confirmation', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
        ('swapped', 'Swapped'),
    ]
    
    ASSIGNMENT_TYPES = [
        ('primary', 'Primary Assignment'),
        ('backup', 'Backup Assignment'),
        ('replacement', 'Replacement'),
        ('emergency', 'Emergency Assignment'),
    ]
    
    # Unique identifier
    assignment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Core Relationships
    shift = models.ForeignKey(
        'scheduling.ShiftInstance',
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shift_assignments'
    )
    
    # Assignment Details
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        default='primary'
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='proposed'
    )
    
    # Timing
    assigned_at = models.DateTimeField(auto_now_add=True)
    confirmation_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for user to confirm assignment"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment Metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignments_made'
    )
    auto_assigned = models.BooleanField(
        default=False,
        help_text="Created by automatic assignment system"
    )
    force_assigned = models.BooleanField(
        default=False,
        help_text="Assignment forced despite warnings"
    )
    
    # Actual hours tracking
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    break_duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Break time in minutes"
    )
    
    # Notes and feedback
    assignment_notes = models.TextField(
        blank=True,
        help_text="Notes from the assigner"
    )
    user_notes = models.TextField(
        blank=True,
        help_text="Notes from the assigned user"
    )
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes after shift completion"
    )
    
    # Audit
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_assignments'
        unique_together = ['shift', 'user', 'assignment_type']
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['user', 'assigned_at']),
            models.Index(fields=['status', 'assigned_at']),
            models.Index(fields=['shift', 'assignment_type']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name()} → {self.shift} ({self.status})"
    
    def get_actual_duration_hours(self):
        """Calculate actual hours worked"""
        if self.actual_start_time and self.actual_end_time:
            duration = self.actual_end_time - self.actual_start_time
            total_minutes = duration.total_seconds() / 60
            actual_minutes = total_minutes - self.break_duration_minutes
            return round(actual_minutes / 60, 2)
        return None
    
    def is_overdue_confirmation(self):
        """Check if confirmation is overdue"""
        if self.status == 'pending_confirmation' and self.confirmation_deadline:
            return timezone.now() > self.confirmation_deadline
        return False
    
    def can_be_cancelled(self):
        """Check if assignment can be cancelled"""
        return (
            self.status in ['proposed', 'pending_confirmation', 'confirmed'] and
            self.shift.can_be_modified()
        )


class AssignmentHistory(models.Model):
    """
    Audit trail for assignment changes
    """
    ACTION_CHOICES = [
        ('created', 'Assignment Created'),
        ('confirmed', 'Assignment Confirmed'),
        ('declined', 'Assignment Declined'),
        ('cancelled', 'Assignment Cancelled'),
        ('completed', 'Assignment Completed'),
        ('modified', 'Assignment Modified'),
        ('swapped', 'Assignment Swapped'),
        ('force_assigned', 'Force Assigned'),
    ]
    
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Who performed the action
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignment_actions'
    )
    
    # Change details
    previous_status = models.CharField(max_length=25, blank=True)
    new_status = models.CharField(max_length=25, blank=True)
    change_reason = models.TextField(blank=True)
    metadata = models.JSONField(
        default=dict,
        help_text="Additional data about the change"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tps_assignment_history'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.assignment.user.get_full_name()} - {self.action} at {self.timestamp}"


class SwapRequest(models.Model):
    """
    Requests for swapping shift assignments between users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved_partial', 'Partially Approved'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    
    # Unique identifier
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Requesting user and their assignment
    requesting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='swap_requests_made'
    )
    requesting_assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='swap_requests_for'
    )
    
    # Target user and their assignment (optional for open requests)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='swap_requests_received'
    )
    target_assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='swap_requests_target'
    )
    
    # Swap Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    swap_type = models.CharField(
        max_length=20,
        choices=[
            ('direct', 'Direct Swap'),
            ('open', 'Open Request'),
            ('partial', 'Partial Coverage'),
        ],
        default='direct'
    )
    
    # Request details
    reason = models.TextField(help_text="Reason for the swap request")
    urgency_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('emergency', 'Emergency'),
        ],
        default='medium'
    )
    
    # Timing
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When the swap request expires"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Approval workflow
    target_user_approved = models.BooleanField(
        null=True,
        help_text="Whether target user has approved"
    )
    manager_approved = models.BooleanField(
        null=True,
        help_text="Whether manager has approved"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='swap_requests_approved'
    )
    
    # Notes
    additional_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'tps_swap_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['requesting_user', 'status']),
            models.Index(fields=['target_user', 'status']),
        ]
        
    def __str__(self):
        target = self.target_user.get_full_name() if self.target_user else "Open"
        return f"Swap: {self.requesting_user.get_full_name()} ↔ {target}"
    
    def is_expired(self):
        """Check if swap request has expired"""
        return timezone.now() > self.expires_at and self.status == 'pending'
    
    def can_be_approved(self):
        """Check if swap can be approved"""
        return (
            self.status == 'pending' and
            not self.is_expired() and
            self.target_user_approved is not False
        )
    
    def requires_manager_approval(self):
        """Check if manager approval is required"""
        # Manager approval required for emergency swaps or cross-team swaps
        return (
            self.urgency_level == 'emergency' or
            (self.target_user and 
             self.requesting_user.team_memberships.first().team != 
             self.target_user.team_memberships.first().team)
        )
