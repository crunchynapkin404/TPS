"""
TPS V1.4 - WebSocket Consumers
Django Channels consumers for real-time functionality
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications
    """
    
    async def connect(self):
        """Accept WebSocket connection and join user notification group"""
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_group_name = f'notifications_user_{self.user_id}'
        
        # Check if user is authenticated and authorized
        user = self.scope.get('user')
        if user and user.is_authenticated:
            if user.id == self.user_id or user.is_superuser or hasattr(user, 'role') and user.role in ['management', 'admin']:
                # Join notification group
                await self.channel_layer.group_add(
                    self.user_group_name,
                    self.channel_name
                )
                await self.accept()
                
                # Send connection confirmation
                await self.send(text_data=json.dumps({
                    'type': 'connection_established',
                    'message': 'Connected to notifications',
                    'user_id': self.user_id
                }))
            else:
                await self.close(code=4003)  # Forbidden
        else:
            await self.close(code=4001)  # Unauthorized
    
    async def disconnect(self, close_code):
        """Leave notification group on disconnect"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'mark_notification_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_read(notification_id)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def assignment_notification(self, event):
        """Handle assignment notification events"""
        await self.send(text_data=json.dumps({
            'type': 'assignment_notification',
            'assignment_id': event['assignment_id'],
            'message': event['message'],
            'shift_date': event['shift_date'],
            'shift_name': event['shift_name'],
            'timestamp': event['timestamp']
        }))
    
    async def planning_notification(self, event):
        """Handle planning notification events"""
        await self.send(text_data=json.dumps({
            'type': 'planning_notification',
            'planning_id': event['planning_id'],
            'message': event['message'],
            'status': event['status'],
            'progress': event.get('progress', 0),
            'timestamp': event['timestamp']
        }))
    
    async def swap_notification(self, event):
        """Handle swap request notification events"""
        await self.send(text_data=json.dumps({
            'type': 'swap_notification',
            'swap_id': event['swap_id'],
            'message': event['message'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))
    
    async def approval_notification(self, event):
        """Handle approval workflow notification events"""
        await self.send(text_data=json.dumps({
            'type': 'approval_notification',
            'request_id': event['request_id'],
            'request_type': event['request_type'],
            'message': event['message'],
            'requires_action': event.get('requires_action', False),
            'timestamp': event['timestamp']
        }))
    
    async def system_notification(self, event):
        """Handle system-wide notification events"""
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'message': event['message'],
            'level': event.get('level', 'info'),
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read in database"""
        try:
            from apps.notifications.models import Notification
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False


class PlanningConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for planning progress updates
    """
    
    async def connect(self):
        """Accept connection and join planning group"""
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.planning_group_name = f'planning_team_{self.team_id}'
        
        # Check authentication and team membership
        user = self.scope.get('user')
        if user and user.is_authenticated:
            has_access = await self.check_team_access(user, self.team_id)
            if has_access:
                await self.channel_layer.group_add(
                    self.planning_group_name,
                    self.channel_name
                )
                await self.accept()
                
                await self.send(text_data=json.dumps({
                    'type': 'connection_established',
                    'message': 'Connected to planning updates',
                    'team_id': self.team_id
                }))
            else:
                await self.close(code=4003)  # Forbidden
        else:
            await self.close(code=4001)  # Unauthorized
    
    async def disconnect(self, close_code):
        """Leave planning group on disconnect"""
        if hasattr(self, 'planning_group_name'):
            await self.channel_layer.group_discard(
                self.planning_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'subscribe_planning':
                planning_id = text_data_json.get('planning_id')
                await self.subscribe_planning_updates(planning_id)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
        except json.JSONDecodeError:
            pass
    
    async def planning_started(self, event):
        """Handle planning generation started events"""
        await self.send(text_data=json.dumps({
            'type': 'planning_started',
            'planning_id': event['planning_id'],
            'message': event['message'],
            'algorithm': event['algorithm'],
            'start_date': event['start_date'],
            'end_date': event['end_date'],
            'timestamp': event['timestamp']
        }))
    
    async def planning_progress(self, event):
        """Handle planning generation progress events"""
        await self.send(text_data=json.dumps({
            'type': 'planning_progress',
            'planning_id': event['planning_id'],
            'progress': event['progress'],
            'current_step': event['current_step'],
            'total_steps': event['total_steps'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))
    
    async def planning_completed(self, event):
        """Handle planning generation completed events"""
        await self.send(text_data=json.dumps({
            'type': 'planning_completed',
            'planning_id': event['planning_id'],
            'success': event['success'],
            'message': event['message'],
            'coverage_percentage': event.get('coverage_percentage'),
            'fairness_score': event.get('fairness_score'),
            'conflicts': event.get('conflicts', []),
            'warnings': event.get('warnings', []),
            'timestamp': event['timestamp']
        }))
    
    async def planning_error(self, event):
        """Handle planning generation error events"""
        await self.send(text_data=json.dumps({
            'type': 'planning_error',
            'planning_id': event['planning_id'],
            'error': event['error'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def check_team_access(self, user, team_id):
        """Check if user has access to team planning"""
        try:
            from apps.teams.models import Team, TeamMembership
            
            # Superusers and management have access to all teams
            if user.is_superuser or getattr(user, 'role', '') in ['management', 'admin', 'planner']:
                return True
            
            # Check team membership
            return TeamMembership.objects.filter(
                team_id=team_id,
                user=user,
                is_active=True
            ).exists()
        except:
            return False
    
    async def subscribe_planning_updates(self, planning_id):
        """Subscribe to specific planning updates"""
        # Add logic to track specific planning subscriptions
        pass


class AssignmentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for assignment updates
    """
    
    async def connect(self):
        """Accept connection and join assignment updates group"""
        self.assignment_group_name = 'assignment_updates'
        
        # Check authentication
        user = self.scope.get('user')
        if user and user.is_authenticated:
            await self.channel_layer.group_add(
                self.assignment_group_name,
                self.channel_name
            )
            await self.accept()
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to assignment updates'
            }))
        else:
            await self.close(code=4001)  # Unauthorized
    
    async def disconnect(self, close_code):
        """Leave assignment group on disconnect"""
        if hasattr(self, 'assignment_group_name'):
            await self.channel_layer.group_discard(
                self.assignment_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'subscribe_team':
                team_id = text_data_json.get('team_id')
                await self.subscribe_team_assignments(team_id)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
        except json.JSONDecodeError:
            pass
    
    async def assignment_created(self, event):
        """Handle assignment created events"""
        await self.send(text_data=json.dumps({
            'type': 'assignment_created',
            'assignment_id': event['assignment_id'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'shift_id': event['shift_id'],
            'shift_name': event['shift_name'],
            'shift_date': event['shift_date'],
            'team_id': event['team_id'],
            'assigned_by': event['assigned_by'],
            'timestamp': event['timestamp']
        }))
    
    async def assignment_updated(self, event):
        """Handle assignment updated events"""
        await self.send(text_data=json.dumps({
            'type': 'assignment_updated',
            'assignment_id': event['assignment_id'],
            'old_status': event['old_status'],
            'new_status': event['new_status'],
            'updated_by': event['updated_by'],
            'timestamp': event['timestamp']
        }))
    
    async def assignment_deleted(self, event):
        """Handle assignment deleted events"""
        await self.send(text_data=json.dumps({
            'type': 'assignment_deleted',
            'assignment_id': event['assignment_id'],
            'shift_date': event['shift_date'],
            'shift_name': event['shift_name'],
            'deleted_by': event['deleted_by'],
            'timestamp': event['timestamp']
        }))
    
    async def conflict_detected(self, event):
        """Handle assignment conflict events"""
        await self.send(text_data=json.dumps({
            'type': 'conflict_detected',
            'conflict_type': event['conflict_type'],
            'assignment_ids': event['assignment_ids'],
            'message': event['message'],
            'severity': event['severity'],
            'timestamp': event['timestamp']
        }))
    
    async def system_status(self, event):
        """Handle system status events"""
        await self.send(text_data=json.dumps({
            'type': 'system_status',
            'status': event['status'],
            'message': event['message'],
            'details': event.get('details', {}),
            'timestamp': event['timestamp']
        }))
    
    async def subscribe_team_assignments(self, team_id):
        """Subscribe to specific team assignment updates"""
        team_group_name = f'assignments_team_{team_id}'
        await self.channel_layer.group_add(
            team_group_name,
            self.channel_name
        )
