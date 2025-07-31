"""
TPS V1.4 - Event Publisher
Service for publishing real-time events via WebSocket
"""

import json
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone


class EventPublisher:
    """
    Service for publishing real-time events to WebSocket consumers
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def _send_to_group(self, group_name, event_data):
        """Send event to WebSocket group"""
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                event_data
            )
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format"""
        return timezone.now().isoformat()
    
    def publish_assignment_created(self, assignment):
        """Publish assignment creation event"""
        # Send to user notification
        user_group = f'notifications_user_{assignment.user.id}'
        self._send_to_group(user_group, {
            'type': 'assignment_notification',
            'assignment_id': assignment.id,
            'message': f'You have been assigned to {assignment.shift.template.name} on {assignment.shift.date}',
            'shift_date': assignment.shift.date.isoformat(),
            'shift_name': assignment.shift.template.name,
            'timestamp': self._get_timestamp()
        })
        
        # Send to team assignment updates
        team_group = f'assignments_team_{assignment.shift.team.id}'
        self._send_to_group(team_group, {
            'type': 'assignment_created',
            'assignment_id': assignment.id,
            'user_id': assignment.user.id,
            'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip(),
            'shift_id': assignment.shift.id,
            'shift_name': assignment.shift.template.name,
            'shift_date': assignment.shift.date.isoformat(),
            'team_id': assignment.shift.team.id,
            'assigned_by': f"{assignment.assigned_by.first_name} {assignment.assigned_by.last_name}".strip(),
            'timestamp': self._get_timestamp()
        })
        
        # Send to general assignment updates
        self._send_to_group('assignment_updates', {
            'type': 'assignment_created',
            'assignment_id': assignment.id,
            'user_id': assignment.user.id,
            'user_name': f"{assignment.user.first_name} {assignment.user.last_name}".strip(),
            'shift_id': assignment.shift.id,
            'shift_name': assignment.shift.template.name,
            'shift_date': assignment.shift.date.isoformat(),
            'team_id': assignment.shift.team.id,
            'assigned_by': f"{assignment.assigned_by.first_name} {assignment.assigned_by.last_name}".strip(),
            'timestamp': self._get_timestamp()
        })
    
    def publish_assignment_updated(self, assignment, old_status, updated_by):
        """Publish assignment update event"""
        # Send to user notification
        user_group = f'notifications_user_{assignment.user.id}'
        self._send_to_group(user_group, {
            'type': 'assignment_notification',
            'assignment_id': assignment.id,
            'message': f'Your assignment status changed from {old_status} to {assignment.status}',
            'shift_date': assignment.shift.date.isoformat(),
            'shift_name': assignment.shift.template.name,
            'timestamp': self._get_timestamp()
        })
        
        # Send to team assignment updates
        team_group = f'assignments_team_{assignment.shift.team.id}'
        self._send_to_group(team_group, {
            'type': 'assignment_updated',
            'assignment_id': assignment.id,
            'old_status': old_status,
            'new_status': assignment.status,
            'updated_by': f"{updated_by.first_name} {updated_by.last_name}".strip(),
            'timestamp': self._get_timestamp()
        })
    
    def publish_assignment_deleted(self, assignment_data, deleted_by):
        """Publish assignment deletion event"""
        # Send to user notification
        user_group = f'notifications_user_{assignment_data["user_id"]}'
        self._send_to_group(user_group, {
            'type': 'assignment_notification',
            'assignment_id': assignment_data['assignment_id'],
            'message': f'Your assignment to {assignment_data["shift_name"]} has been cancelled',
            'shift_date': assignment_data['shift_date'],
            'shift_name': assignment_data['shift_name'],
            'timestamp': self._get_timestamp()
        })
        
        # Send to team assignment updates
        team_group = f'assignments_team_{assignment_data["team_id"]}'
        self._send_to_group(team_group, {
            'type': 'assignment_deleted',
            'assignment_id': assignment_data['assignment_id'],
            'shift_date': assignment_data['shift_date'],
            'shift_name': assignment_data['shift_name'],
            'deleted_by': f"{deleted_by.first_name} {deleted_by.last_name}".strip(),
            'timestamp': self._get_timestamp()
        })
    
    def publish_planning_started(self, planning_request, team):
        """Publish planning generation started event"""
        team_group = f'planning_team_{team.id}'
        self._send_to_group(team_group, {
            'type': 'planning_started',
            'planning_id': planning_request.get('id', 0),
            'message': f'Planning generation started for {team.name}',
            'algorithm': planning_request.get('algorithm', 'balanced'),
            'start_date': planning_request.get('start_date', ''),
            'end_date': planning_request.get('end_date', ''),
            'timestamp': self._get_timestamp()
        })
    
    def publish_planning_progress(self, planning_id, team, progress, current_step, total_steps, message):
        """Publish planning generation progress event"""
        team_group = f'planning_team_{team.id}'
        self._send_to_group(team_group, {
            'type': 'planning_progress',
            'planning_id': planning_id,
            'progress': progress,
            'current_step': current_step,
            'total_steps': total_steps,
            'message': message,
            'timestamp': self._get_timestamp()
        })
    
    def publish_planning_completed(self, planning_result, team):
        """Publish planning generation completed event"""
        team_group = f'planning_team_{team.id}'
        self._send_to_group(team_group, {
            'type': 'planning_completed',
            'planning_id': planning_result.planning_period_id if hasattr(planning_result, 'planning_period_id') else 0,
            'success': planning_result.success,
            'message': 'Planning generation completed successfully' if planning_result.success else 'Planning generation failed',
            'coverage_percentage': getattr(planning_result, 'coverage_percentage', 0),
            'fairness_score': getattr(planning_result, 'fairness_score', 0),
            'conflicts': getattr(planning_result, 'conflicts', []),
            'warnings': getattr(planning_result, 'warnings', []),
            'timestamp': self._get_timestamp()
        })
        
        # Notify team members of completed planning
        if planning_result.success:
            team_members = team.memberships.filter(is_active=True).values_list('user_id', flat=True)
            for user_id in team_members:
                user_group = f'notifications_user_{user_id}'
                self._send_to_group(user_group, {
                    'type': 'planning_notification',
                    'planning_id': planning_result.planning_period_id if hasattr(planning_result, 'planning_period_id') else 0,
                    'message': f'New planning has been generated for {team.name}',
                    'status': 'completed',
                    'timestamp': self._get_timestamp()
                })
    
    def publish_planning_error(self, planning_id, team, error_message):
        """Publish planning generation error event"""
        team_group = f'planning_team_{team.id}'
        self._send_to_group(team_group, {
            'type': 'planning_error',
            'planning_id': planning_id,
            'error': error_message,
            'message': f'Planning generation failed: {error_message}',
            'timestamp': self._get_timestamp()
        })
    
    def publish_approval_required(self, approval_request, approver):
        """Publish approval required event"""
        user_group = f'notifications_user_{approver.id}'
        self._send_to_group(user_group, {
            'type': 'approval_notification',
            'request_id': approval_request.get('id', 0),
            'request_type': approval_request.get('type', 'unknown'),
            'message': f'Approval required: {approval_request.get("description", "")}',
            'requires_action': True,
            'timestamp': self._get_timestamp()
        })
    
    def publish_swap_request_created(self, swap_request):
        """Publish swap request creation event"""
        # Notify both users involved in the swap
        from_user_group = f'notifications_user_{swap_request.from_assignment.user.id}'
        to_user_group = f'notifications_user_{swap_request.to_assignment.user.id}'
        
        message = f'Swap request created for shifts on {swap_request.from_assignment.shift.date} and {swap_request.to_assignment.shift.date}'
        
        for user_group in [from_user_group, to_user_group]:
            self._send_to_group(user_group, {
                'type': 'swap_notification',
                'swap_id': swap_request.id,
                'message': message,
                'status': swap_request.status,
                'timestamp': self._get_timestamp()
            })
    
    def publish_swap_request_approved(self, swap_request, approved_by):
        """Publish swap request approval event"""
        from_user_group = f'notifications_user_{swap_request.from_assignment.user.id}'
        to_user_group = f'notifications_user_{swap_request.to_assignment.user.id}'
        
        message = f'Swap request approved by {approved_by.first_name} {approved_by.last_name}'
        
        for user_group in [from_user_group, to_user_group]:
            self._send_to_group(user_group, {
                'type': 'swap_notification',
                'swap_id': swap_request.id,
                'message': message,
                'status': 'approved',
                'timestamp': self._get_timestamp()
            })
    
    def publish_swap_request_rejected(self, swap_request, rejected_by, reason):
        """Publish swap request rejection event"""
        user_group = f'notifications_user_{swap_request.requested_by.id}'
        
        message = f'Swap request rejected by {rejected_by.first_name} {rejected_by.last_name}: {reason}'
        
        self._send_to_group(user_group, {
            'type': 'swap_notification',
            'swap_id': swap_request.id,
            'message': message,
            'status': 'rejected',
            'timestamp': self._get_timestamp()
        })
    
    def publish_conflict_detected(self, conflict_type, assignment_ids, message, severity='warning'):
        """Publish assignment conflict detection event"""
        self._send_to_group('assignment_updates', {
            'type': 'conflict_detected',
            'conflict_type': conflict_type,
            'assignment_ids': assignment_ids,
            'message': message,
            'severity': severity,
            'timestamp': self._get_timestamp()
        })
    
    def publish_system_status(self, status, message, details=None):
        """Publish system status event"""
        self._send_to_group('assignment_updates', {
            'type': 'system_status',
            'status': status,
            'message': message,
            'details': details or {},
            'timestamp': self._get_timestamp()
        })
    
    def publish_leave_request_submitted(self, leave_request):
        """Publish leave request submission event"""
        # Notify user
        user_group = f'notifications_user_{leave_request.user.id}'
        self._send_to_group(user_group, {
            'type': 'approval_notification',
            'request_id': leave_request.id,
            'request_type': 'leave_request',
            'message': f'Leave request submitted for {leave_request.start_date} to {leave_request.end_date}',
            'requires_action': False,
            'timestamp': self._get_timestamp()
        })
        
        # Notify approvers (team leaders and management)
        team_leaders = leave_request.user.teams.filter(
            teammembership__role__is_leadership=True,
            teammembership__is_active=True
        ).values_list('teammembership__user_id', flat=True)
        
        for approver_id in team_leaders:
            approver_group = f'notifications_user_{approver_id}'
            self._send_to_group(approver_group, {
                'type': 'approval_notification',
                'request_id': leave_request.id,
                'request_type': 'leave_request',
                'message': f'Leave request from {leave_request.user.first_name} {leave_request.user.last_name} requires approval',
                'requires_action': True,
                'timestamp': self._get_timestamp()
            })
    
    def publish_leave_request_approved(self, leave_request, approved_by):
        """Publish leave request approval event"""
        user_group = f'notifications_user_{leave_request.user.id}'
        
        self._send_to_group(user_group, {
            'type': 'approval_notification',
            'request_id': leave_request.id,
            'request_type': 'leave_request',
            'message': f'Leave request approved by {approved_by.first_name} {approved_by.last_name}',
            'requires_action': False,
            'timestamp': self._get_timestamp()
        })
    
    def publish_leave_request_rejected(self, leave_request, rejected_by, reason):
        """Publish leave request rejection event"""
        user_group = f'notifications_user_{leave_request.user.id}'
        
        self._send_to_group(user_group, {
            'type': 'approval_notification',
            'request_id': leave_request.id,
            'request_type': 'leave_request',
            'message': f'Leave request rejected by {rejected_by.first_name} {rejected_by.last_name}: {reason}',
            'requires_action': False,
            'timestamp': self._get_timestamp()
        })


# Global event publisher instance
event_publisher = EventPublisher()
