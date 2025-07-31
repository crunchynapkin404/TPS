from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    ShiftCategory, ShiftTemplate, ShiftInstance, 
    PlanningPeriod
)


@admin.register(ShiftCategory)
class ShiftCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'display_name', 
        'get_color_display',
        'max_weeks_per_year',
        'hours_per_week',
        'allows_auto_assignment'
    ]
    list_filter = ['allows_auto_assignment', 'requires_handover']
    search_fields = ['name', 'display_name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'description', 'color')
        }),
        ('Business Rules', {
            'fields': (
                'max_weeks_per_year', 
                'hours_per_week', 
                'min_gap_days',
                'priority_weight'
            )
        }),
        ('Configuration', {
            'fields': ('requires_handover', 'allows_auto_assignment'),
            'classes': ('collapse',)
        }),
    )
    
    def get_color_display(self, obj):
        return format_html(
            '<div class="w-5 h-5 border border-gray-300 rounded" style="background-color: {};"></div>',
            obj.color
        )


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'get_time_display', 
        'duration_hours',
        'is_weekly_shift',
        'spans_weekend',
        'get_team_count'
    ]
    list_filter = [
        'category',
        'is_overnight',
        'is_weekly_shift', 
        'spans_weekend'
    ]
    search_fields = ['name', 'description', 'category__display_name']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration_hours')
        }),
        ('Characteristics', {
            'fields': (
                'is_overnight', 
                'is_weekly_shift', 
                'spans_weekend',
                'days_of_week'
            ),
            'classes': ('collapse',)
        }),
        ('Requirements', {
            'fields': (
                'engineers_required',
                'backup_engineers',
                'required_skills'
            ),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': (
                'is_active',
                'location'
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_time_display(self, obj):
        return f"{obj.start_time} - {obj.end_time}"
    
    def get_team_count(self, obj):
        # This would need to be implemented based on actual relationships
        return "TBD"


class ShiftInstanceInline(admin.TabularInline):
    model = ShiftInstance
    extra = 0
    fields = ['start_datetime', 'end_datetime', 'status', 'template']
    readonly_fields = ['created_at']


@admin.register(PlanningPeriod)
class PlanningPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'period_type',
        'start_date', 
        'end_date',
        'status',
        'get_shifts_count'
    ]
    list_filter = ['period_type', 'status', 'start_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'
    inlines = [ShiftInstanceInline]
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'description', 'period_type')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Configuration', {
            'fields': ('auto_generate_shifts', 'status'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['created_by']
    
    def get_shifts_count(self, obj):
        count = obj.shifts.count()
        return format_html('<span>{} shifts</span>', count)


@admin.register(ShiftInstance)
class ShiftInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'get_shift_display',
        'start_datetime',
        'end_datetime', 
        'status',
        'get_assignments_display',
        'planning_period'
    ]
    list_filter = [
        'template__category',
        'status',
        'start_datetime',
        'planning_period'
    ]
    search_fields = [
        'template__name',
        'planning_period__name',
        'notes'
    ]
    date_hierarchy = 'start_datetime'
    autocomplete_fields = ['template', 'planning_period']
    
    fieldsets = (
        ('Shift Information', {
            'fields': ('template', 'planning_period')
        }),
        ('Timing', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Staffing', {
            'fields': ('status', 'notes')
        }),
        ('Additional Information', {
            'fields': ('special_instructions', 'is_emergency'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_shift_display(self, obj):
        return f"{obj.template.name}"
    
    def get_assignments_display(self, obj):
        # This would show assignment count when assignments model is available
        return "0/0"  # Placeholder
