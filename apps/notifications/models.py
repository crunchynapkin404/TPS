"""
TPS V1.4 - Notifications Models
Real-time notifications and activity tracking
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class NotificationType(models.Model):
    """
    Types of notifications that can be sent
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    
    # Notification characteristics
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    requires_action = models.BooleanField(
        default=False,
        help_text="Whether this notification requires user action"
    )
    auto_expire_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Hours after which notification auto-expires"
    )
    
    # Delivery methods
    send_email = models.BooleanField(
        default=False,
        help_text="Send email notifications"
    )
    send_realtime = models.BooleanField(
        default=True,
        help_text="Send real-time notifications"
    )
    send_sms = models.BooleanField(
        default=False,
        help_text="Send SMS notifications"
    )
    
    # Template
    title_template = models.CharField(
        max_length=200,
        help_text="Template for notification title (supports variables)"
    )
    message_template = models.TextField(
        help_text="Template for notification message (supports variables)"
    )
    
    # UI configuration
    icon = models.CharField(
        max_length=50,
        default='bell',
        help_text="FontAwesome icon name"
    )
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Color for notification display"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tps_notification_types'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Individual notification instances sent to users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('acknowledged', 'Acknowledged'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    
    # Unique identifier
    notification_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Core notification details
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.URLField(
        blank=True,
        help_text="URL for action button"
    )
    action_text = models.CharField(
        max_length=50,
        blank=True,
        help_text="Text for action button"
    )
    
    # Status and timing
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects (generic foreign key would be ideal, but keeping simple)
    related_assignment_id = models.UUIDField(null=True, blank=True)
    related_leave_request_id = models.UUIDField(null=True, blank=True)
    related_swap_request_id = models.UUIDField(null=True, blank=True)
    
    # Delivery tracking
    email_sent = models.BooleanField(default=False)
    email_delivered = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    sms_delivered = models.BooleanField(default=False)
    
    # Metadata
    context_data = models.JSONField(
        default=dict,
        help_text="Additional context data for the notification"
    )
    
    class Meta:
        db_table = 'tps_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['status', 'expires_at']),
        ]
        
    def __str__(self):
        return f"{self.notification_type.name} → {self.recipient.get_full_name()}"
    
    def is_expired(self):
        """Check if notification has expired"""
        return (
            self.expires_at and 
            timezone.now() > self.expires_at and 
            self.status not in ['read', 'acknowledged']
        )
    
    def mark_as_read(self):
        """Mark notification as read"""
        if self.status in ['sent', 'delivered']:
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def mark_as_acknowledged(self):
        """Mark notification as acknowledged"""
        if self.status in ['sent', 'delivered', 'read']:
            self.status = 'acknowledged'
            self.acknowledged_at = timezone.now()
            self.save(update_fields=['status', 'acknowledged_at'])
    
    def can_be_acknowledged(self):
        """Check if notification can be acknowledged"""
        return (
            self.notification_type.requires_action and
            self.status in ['sent', 'delivered', 'read'] and
            not self.is_expired()
        )


class NotificationPreference(models.Model):
    """
    User preferences for notification delivery
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='user_preferences'
    )
    
    # Delivery preferences
    email_enabled = models.BooleanField(default=True)
    realtime_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    
    # Timing preferences
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_start_time = models.TimeField(null=True, blank=True)
    quiet_end_time = models.TimeField(null=True, blank=True)
    
    # Grouping preferences
    digest_enabled = models.BooleanField(
        default=False,
        help_text="Group similar notifications into digest"
    )
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='immediate'
    )
    
    # Audit
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tps_notification_preferences'
        unique_together = ['user', 'notification_type']
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.notification_type.name}"
    
    def is_in_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_start_time or not self.quiet_end_time:
            return False
        
        current_time = timezone.now().time()
        
        if self.quiet_start_time <= self.quiet_end_time:
            # Same day quiet hours (e.g., 22:00 - 08:00 next day)
            return self.quiet_start_time <= current_time <= self.quiet_end_time
        else:
            # Overnight quiet hours (e.g., 22:00 - 08:00 next day)
            return current_time >= self.quiet_start_time or current_time <= self.quiet_end_time


class NotificationQueue(models.Model):
    """
    Queue for notifications to be processed
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='queue_entry'
    )
    
    # Queue details
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='queued')
    scheduled_for = models.DateTimeField(
        default=timezone.now,
        help_text="When to send the notification"
    )
    
    # Retry logic
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_error = models.TextField(blank=True)
    
    # Processing tracking
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tps_notification_queue'
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
        ]
        
    def __str__(self):
        return f"Queue: {self.notification.title} ({self.status})"
    
    def can_retry(self):
        """Check if notification can be retried"""
        return self.retry_count < self.max_retries and self.status == 'failed'
    
    def is_ready_to_send(self):
        """Check if notification is ready to be sent"""
        return (
            self.status == 'queued' and
            timezone.now() >= self.scheduled_for
        )
