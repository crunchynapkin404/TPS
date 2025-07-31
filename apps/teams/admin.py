from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from .models import Team, TeamRole, TeamMembership, TeamScheduleTemplate


class TeamAdminForm(forms.ModelForm):
    """Custom form for Team admin with better JSON field handling"""
    
    class Meta:
        model = Team
        fields = '__all__'
        widgets = {
            'notification_preferences': forms.Textarea(attrs={
                'rows': 8,
                'cols': 60,
                'placeholder': '{\n  "email_enabled": true,\n  "shift_reminders": true,\n  "swap_notifications": true\n}'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default JSON if field is empty
        if not self.instance.pk or not self.instance.notification_preferences:
            self.fields['notification_preferences'].initial = {
                "email_enabled": True,
                "shift_reminders": True,
                "swap_notifications": True,
                "assignment_updates": True
            }


@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_name_display', 'can_assign_shifts', 'can_approve_swaps', 'can_manage_team']
    list_filter = ['can_assign_shifts', 'can_approve_swaps', 'can_manage_team']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Permissions', {
            'fields': ('can_assign_shifts', 'can_approve_swaps', 'can_manage_team'),
            'classes': ('collapse',)
        }),
    )


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    fields = ['user', 'role', 'is_active', 'is_primary_team', 'availability_percentage', 'join_date']
    autocomplete_fields = ['user']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'role')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
    list_display = [
        'name', 
        'department', 
        'get_member_count_display', 
        'team_leader', 
        'location',
        'is_active',
        'created_at'
    ]
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'department', 'location']
    autocomplete_fields = ['team_leader']
    inlines = [TeamMembershipInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'department', 'location', 'team_leader')
        }),
        ('Staffing Configuration', {
            'fields': ('min_members_per_shift', 'max_members_per_shift', 'preferred_team_size'),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('is_active', 'allows_auto_assignment', 'notification_preferences'),
            'classes': ('collapse',),
            'description': 'Notification preferences should be valid JSON. Example: {"email_enabled": true, "shift_reminders": true}'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_member_count_display(self, obj):
        count = obj.get_member_count()
        css_class = 'text-green-600' if count >= obj.min_members_per_shift else 'text-red-600'
        return format_html(
            '<span class="{}">{} members</span>',
            css_class,
            count
        )
    get_member_count_display.short_description = 'Active Members'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('memberships__user')


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'team', 
        'role',
        'is_active',
        'is_primary_team',
        'availability_percentage',
        'join_date'
    ]
    list_filter = [
        'is_active', 
        'is_primary_team', 
        'role__name',
        'team__department',
        'prefers_waakdienst',
        'prefers_incident'
    ]
    search_fields = [
        'user__first_name', 
        'user__last_name', 
        'user__employee_id',
        'team__name'
    ]
    autocomplete_fields = ['user', 'team', 'role']
    date_hierarchy = 'join_date'
    
    fieldsets = (
        ('Basic Assignment', {
            'fields': ('user', 'team', 'role', 'is_active')
        }),
        ('Membership Details', {
            'fields': ('is_primary_team', 'availability_percentage', 'join_date', 'leave_date')
        }),
        ('Shift Preferences', {
            'fields': (
                'prefers_waakdienst', 
                'prefers_incident', 
                'weekend_availability', 
                'night_shift_availability'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'team', 'role')


@admin.register(TeamScheduleTemplate)
class TeamScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'team', 'template_type', 'effective_start_date', 'is_active']
    list_filter = ['template_type', 'is_active', 'team__department']
    search_fields = ['name', 'team__name']
    autocomplete_fields = ['team', 'created_by']
    date_hierarchy = 'effective_start_date'
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'team', 'template_type', 'pattern_data')
        }),
        ('Effective Period', {
            'fields': ('effective_start_date', 'effective_end_date', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )


# Customize admin site header and title
admin.site.site_header = "TPS V1.4 Administration"
admin.site.site_title = "TPS Admin"
admin.site.index_title = "Team Planning System Administration"
