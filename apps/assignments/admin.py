from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Assignment, AssignmentHistory, SwapRequest


class AssignmentHistoryInline(admin.TabularInline):
    model = AssignmentHistory
    extra = 0
    fields = ['action', 'actor', 'previous_status', 'new_status', 'timestamp']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request, obj=None):
        return False  # History entries are auto-generated


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'get_user_display',
        'get_shift_display',
        'assignment_type',
        'status',
        'get_status_badge',
        'assigned_at',
        'get_duration_display'
    ]
    list_filter = [
        'status',
        'assignment_type',
        'auto_assigned',
        'force_assigned',
        'assigned_at',
        'shift__template__category'
    ]
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'shift__template__name',
        'assignment_notes',
        'user_notes'
    ]
    date_hierarchy = 'assigned_at'
    autocomplete_fields = ['user', 'shift', 'assigned_by']
    inlines = [AssignmentHistoryInline]
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('user', 'shift', 'assignment_type', 'status')
        }),
        ('Assignment Details', {
            'fields': ('assigned_by', 'auto_assigned', 'force_assigned')
        }),
        ('Timing', {
            'fields': (
                'assigned_at',
                'confirmation_deadline',
                'confirmed_at',
                'completed_at'
            )
        }),
        ('Actual Hours', {
            'fields': (
                'actual_start_time',
                'actual_end_time',
                'break_duration_minutes'
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': (
                'assignment_notes',
                'user_notes',
                'completion_notes'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['assigned_at', 'updated_at']
    
    def get_user_display(self, obj):
        return obj.user.get_full_name()
    
    def get_shift_display(self, obj):
        return f"{obj.shift.template.name} - {obj.shift.date}"
    
    def get_status_badge(self, obj):
        colors = {
            'proposed': '#6B7280',
            'pending_confirmation': '#F59E0B',
            'confirmed': '#10B981',
            'declined': '#EF4444',
            'completed': '#8B5CF6',
            'no_show': '#DC2626',
            'cancelled': '#6B7280',
            'swapped': '#3B82F6'
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    def get_duration_display(self, obj):
        duration = obj.get_actual_duration_hours()
        if duration:
            return f"{duration}h"
        return f"{obj.shift.template.duration_hours}h (planned)"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'shift__template', 'assigned_by'
        )


@admin.register(AssignmentHistory)
class AssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'get_assignment_display',
        'action',
        'get_actor_display',
        'get_status_change',
        'timestamp'
    ]
    list_filter = [
        'action',
        'timestamp',
        'assignment__status'
    ]
    search_fields = [
        'assignment__user__first_name',
        'assignment__user__last_name',
        'actor__first_name',
        'actor__last_name',
        'change_reason'
    ]
    date_hierarchy = 'timestamp'
    autocomplete_fields = ['assignment', 'actor']
    
    fieldsets = (
        ('History Entry', {
            'fields': ('assignment', 'action', 'actor')
        }),
        ('Change Details', {
            'fields': ('previous_status', 'new_status', 'change_reason')
        }),
        ('Metadata', {
            'fields': ('metadata', 'timestamp'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['timestamp']
    
    def get_assignment_display(self, obj):
        return f"{obj.assignment.user.get_full_name()} → {obj.assignment.shift.template.name}"
    
    def get_actor_display(self, obj):
        return obj.actor.get_full_name() if obj.actor else "System"
    
    def get_status_change(self, obj):
        if obj.previous_status and obj.new_status:
            return f"{obj.previous_status} → {obj.new_status}"
        return obj.action
    
    def has_add_permission(self, request):
        return False  # History entries are auto-generated
    
    def has_change_permission(self, request, obj=None):
        return False  # History entries should not be modified


@admin.register(SwapRequest)
class SwapRequestAdmin(admin.ModelAdmin):
    list_display = [
        'get_request_display',
        'swap_type',
        'urgency_level',
        'get_status_badge',
        'get_approval_status',
        'requested_at',
        'expires_at'
    ]
    list_filter = [
        'status',
        'swap_type',
        'urgency_level',
        'target_user_approved',
        'manager_approved',
        'requested_at'
    ]
    search_fields = [
        'requesting_user__first_name',
        'requesting_user__last_name',
        'target_user__first_name',
        'target_user__last_name',
        'reason',
        'additional_notes'
    ]
    date_hierarchy = 'requested_at'
    autocomplete_fields = ['requesting_user', 'target_user', 'requesting_assignment', 'target_assignment', 'approved_by']
    
    fieldsets = (
        ('Swap Request', {
            'fields': (
                'requesting_user',
                'requesting_assignment',
                'target_user',
                'target_assignment'
            )
        }),
        ('Request Details', {
            'fields': ('swap_type', 'urgency_level', 'reason')
        }),
        ('Status & Timing', {
            'fields': (
                'status',
                'requested_at',
                'expires_at',
                'resolved_at'
            )
        }),
        ('Approval Workflow', {
            'fields': (
                'target_user_approved',
                'manager_approved',
                'approved_by'
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('additional_notes', 'resolution_notes'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['requested_at', 'resolved_at']
    
    def get_request_display(self, obj):
        target = obj.target_user.get_full_name() if obj.target_user else "Open Request"
        return f"{obj.requesting_user.get_full_name()} ↔ {target}"
    
    def get_status_badge(self, obj):
        colors = {
            'pending': '#F59E0B',
            'approved_partial': '#3B82F6',
            'approved': '#10B981',
            'declined': '#EF4444',
            'cancelled': '#6B7280',
            'completed': '#8B5CF6',
            'expired': '#DC2626'
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    def get_approval_status(self, obj):
        approvals = []
        if obj.target_user_approved is True:
            approvals.append('👤 User')
        elif obj.target_user_approved is False:
            approvals.append('❌ User')
        
        if obj.manager_approved is True:
            approvals.append('👔 Manager')
        elif obj.manager_approved is False:
            approvals.append('❌ Manager')
            
        return ' | '.join(approvals) if approvals else 'Pending'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'requesting_user', 'target_user', 'requesting_assignment__shift__template',
            'target_assignment__shift__template', 'approved_by'
        )
