"""
Notification Service for TPS V1.4
Handles notification creation, delivery, and real-time communication
"""

import logging
from typing import List, Dict, Optional, Any
from django.utils import timezone

from apps.accounts.models import User
from apps.assignments.models import Assignment, SwapRequest
from apps.leave_management.models import LeaveRequest
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing notifications and real-time communication
    """
    
    def __init__(self):
        pass
    
    def notify_assignment_created(self, assignment: Assignment) -> bool:
        """
        Send notification when a new assignment is created
        """
        try:
            notification = Notification.objects.create(
                user=assignment.user,
                type='ASSIGNMENT_CREATED',
                title='New Shift Assignment',
                message=f'You have been assigned to {assignment.shift_instance.template.name} on {assignment.shift_instance.date}',
                data={
                    'assignment_id': assignment.id,
                    'shift_date': assignment.shift_instance.date.isoformat(),
                    'shift_name': assignment.shift_instance.template.name,
                    'shift_category': assignment.shift_instance.template.category
                },
                is_read=False,
                created_at=timezone.now()
            )
            
            # Send real-time notification
            self.send_real_time_notification(assignment.user, notification)
            
            logger.info(f"Assignment notification sent to {assignment.user.get_full_name()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send assignment notification: {str(e)}")
            return False
    
    def notify_leave_request_submitted(self, leave_request: LeaveRequest) -> bool:
        """
        Send notification when a leave request is submitted
        """
        try:
            # Notify the user who submitted the request
            user_notification = Notification.objects.create(
                user=leave_request.user,
                type='LEAVE_REQUEST_SUBMITTED',
                title='Leave Request Submitted',
                message=f'Your leave request for {leave_request.start_date} to {leave_request.end_date} has been submitted for approval',
                data={
                    'leave_request_id': leave_request.id,
                    'start_date': leave_request.start_date.isoformat(),
                    'end_date': leave_request.end_date.isoformat(),
                    'leave_type': leave_request.leave_type
                },
                is_read=False,
                created_at=timezone.now()
            )
            
            self.send_real_time_notification(leave_request.user, user_notification)
            
            # Notify managers/approvers
            # This would be enhanced to get actual approvers from team hierarchy
            logger.info(f"Leave request notification sent to {leave_request.user.get_full_name()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send leave request notification: {str(e)}")
            return False
    
    def notify_swap_request_created(self, swap_request: SwapRequest) -> bool:
        """
        Send notification when a swap request is created
        """
        try:
            # Notify the user who requested the swap
            requester_notification = Notification.objects.create(
                user=swap_request.requested_by,
                type='SWAP_REQUEST_CREATED',
                title='Swap Request Created',
                message=f'Your swap request for {swap_request.original_assignment.shift_instance.date} has been created',
                data={
                    'swap_request_id': swap_request.id,
                    'original_assignment_id': swap_request.original_assignment.id,
                    'shift_date': swap_request.original_assignment.shift_instance.date.isoformat()
                },
                is_read=False,
                created_at=timezone.now()
            )
            
            self.send_real_time_notification(swap_request.requested_by, requester_notification)
            
            # If there's a target user, notify them too
            if swap_request.target_user:
                target_notification = Notification.objects.create(
                    user=swap_request.target_user,
                    type='SWAP_REQUEST_RECEIVED',
                    title='Swap Request Received',
                    message=f'{swap_request.requested_by.get_full_name()} wants to swap shifts with you',
                    data={
                        'swap_request_id': swap_request.id,
                        'requester_name': swap_request.requested_by.get_full_name(),
                        'shift_date': swap_request.original_assignment.shift_instance.date.isoformat()
                    },
                    is_read=False,
                    created_at=timezone.now()
                )
                
                self.send_real_time_notification(swap_request.target_user, target_notification)
            
            logger.info(f"Swap request notifications sent for request {swap_request.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send swap request notification: {str(e)}")
            return False
    
    def notify_planning_generated(self, planning_result: Dict[str, Any], team_users: List[User]) -> bool:
        """
        Send notification when planning is generated
        """
        try:
            success_count = 0
            
            for user in team_users:
                notification = Notification.objects.create(
                    user=user,
                    type='PLANNING_GENERATED',
                    title='New Schedule Generated',
                    message=f'A new schedule has been generated with {planning_result.get("total_assignments", 0)} assignments',
                    data={
                        'planning_success': planning_result.get('success', False),
                        'total_assignments': planning_result.get('total_assignments', 0),
                        'generation_time': timezone.now().isoformat()
                    },
                    is_read=False,
                    created_at=timezone.now()
                )
                
                if self.send_real_time_notification(user, notification):
                    success_count += 1
            
            logger.info(f"Planning notifications sent to {success_count}/{len(team_users)} users")
            return success_count == len(team_users)
            
        except Exception as e:
            logger.error(f"Failed to send planning notifications: {str(e)}")
            return False
    
    def send_real_time_notification(self, user: User, notification: Notification) -> bool:
        """
        Send real-time notification via WebSocket
        This would integrate with Django Channels
        """
        try:
            # This is a placeholder for WebSocket integration
            # In a real implementation, this would use Django Channels
            # to send messages to connected WebSocket consumers
            
            notification_data = {
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read
            }
            
            # Placeholder for WebSocket channel send
            # channel_layer = get_channel_layer()
            # async_to_sync(channel_layer.group_send)(
            #     f"user_{user.id}",
            #     {
            #         'type': 'notification_message',
            #         'notification': notification_data
            #     }
            # )
            
            logger.debug(f"Real-time notification sent to user {user.id}: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send real-time notification: {str(e)}")
            return False
    
    def send_email_notification(self, user: User, notification: Notification) -> bool:
        """
        Send email notification
        This would integrate with Django's email system
        """
        try:
            # This is a placeholder for email integration
            # In a real implementation, this would use Django's email system
            
            # from django.core.mail import send_mail
            # send_mail(
            #     subject=notification.title,
            #     message=notification.message,
            #     from_email='noreply@tps.com',
            #     recipient_list=[user.email],
            #     fail_silently=False,
            # )
            
            logger.debug(f"Email notification sent to {user.email}: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def get_user_notifications(
        self, 
        user: User, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a specific user
        """
        queryset = Notification.objects.filter(user=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
            
        return list(queryset.order_by('-created_at')[:limit])
    
    def mark_notification_read(self, notification: Notification) -> bool:
        """
        Mark a notification as read
        """
        try:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
            return False
    
    def mark_all_notifications_read(self, user: User) -> int:
        """
        Mark all notifications as read for a user
        Returns count of updated notifications
        """
        try:
            updated_count = Notification.objects.filter(
                user=user, is_read=False
            ).update(is_read=True)
            
            logger.info(f"Marked {updated_count} notifications as read for {user.get_full_name()}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to mark notifications as read: {str(e)}")
            return 0
    
    def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """
        Clean up notifications older than specified days
        Returns count of deleted notifications
        """
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
            deleted_count, _ = Notification.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {deleted_count} old notifications")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {str(e)}")
            return 0
