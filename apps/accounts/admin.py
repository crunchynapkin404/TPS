from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import User, SkillCategory, Skill, UserSkill


class UserSkillInline(admin.TabularInline):
    model = UserSkill
    extra = 1
    autocomplete_fields = ['skill']
    fields = ['skill', 'proficiency_level', 'is_certified', 'certification_date']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Extend the default UserAdmin
    list_display = [
        'username', 
        'employee_id',
        'first_name', 
        'last_name', 
        'email',
        'role',
        'get_role_badge',
        'get_ytd_summary',
        'is_active_employee',
        'date_joined'
    ]
    list_filter = list(BaseUserAdmin.list_filter) + [
        'role',
        'is_active_employee',
        'ytd_waakdienst_weeks',
        'ytd_incident_weeks'
    ]
    search_fields = list(BaseUserAdmin.search_fields) + ['employee_id']
    
    # Add custom fieldsets
    fieldsets = list(BaseUserAdmin.fieldsets) + [
        ('Role & Permissions', {
            'fields': ('role',),
            'description': 'User role determines access level in the TPS system'
        }),
        ('Employee Information', {
            'fields': ('employee_id', 'phone', 'emergency_contact', 'emergency_phone')
        }),
        ('Year-to-Date Tracking', {
            'fields': ('ytd_waakdienst_weeks', 'ytd_incident_weeks', 'ytd_hours_logged'),
            'classes': ('collapse',)
        }),
        ('Availability Preferences', {
            'fields': (
                'preferred_shift_types', 
                'blackout_dates', 
                'max_consecutive_days'
            ),
            'classes': ('collapse',)
        }),
        ('Employee Status', {
            'fields': ('is_active_employee',)
        }),
    ]
    
    add_fieldsets = list(BaseUserAdmin.add_fieldsets) + [
        ('Employee Information', {
            'fields': ('employee_id', 'first_name', 'last_name', 'email')
        }),
    ]
    
    inlines = [UserSkillInline]
    readonly_fields = ['date_joined', 'last_login']
    
    def get_role_badge(self, obj):
        """Display role as colored badge using CSS classes"""
        role_classes = {
            'USER': 'bg-gray-500',      # Gray
            'PLANNER': 'bg-blue-500',   # Blue  
            'MANAGER': 'bg-amber-500',  # Amber
            'ADMIN': 'bg-red-500',      # Red
        }
        css_class = role_classes.get(obj.role, 'bg-gray-500')
        return format_html(
            '<span class="{} text-white px-2 py-1 rounded-full text-xs font-bold">{}</span>',
            css_class,
            obj.get_role_display()
        )
    get_role_badge.short_description = 'Role'
    
    def get_ytd_summary(self, obj):
        stats = obj.get_ytd_stats()
        return format_html(
            '<div>W: {}/{} | I: {}/{}</div>',
            stats['waakdienst_weeks'],
            8,
            stats['incident_weeks'], 
            12
        )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('user_skills__skill')


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'get_color_display', 
        'get_skills_count',
        'is_active'
    ]
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'color')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def get_color_display(self, obj):
        return format_html(
            '<div class="w-5 h-5 border border-gray-300 rounded" style="background-color: {};"></div>',
            obj.color
        )
    
    def get_skills_count(self, obj):
        count = obj.skills.count()
        return format_html('<span>{} skills</span>', count)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'category', 
        'minimum_level_required',
        'requires_certification',
        'is_active',
        'get_users_count'
    ]
    list_filter = [
        'category', 
        'minimum_level_required',
        'requires_certification',
        'is_active'
    ]
    search_fields = ['name', 'description', 'category__name']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Requirements', {
            'fields': (
                'minimum_level_required', 
                'requires_certification',
                'certification_validity_months'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_users_count(self, obj):
        count = obj.user_skills.filter(user__is_active_employee=True).count()
        return format_html('<span>{} users</span>', count)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'skill',
        'proficiency_level',
        'is_certified',
        'certification_expiry'
    ]
    list_filter = [
        'proficiency_level',
        'is_certified',
        'skill__category'
    ]
    search_fields = [
        'user__first_name',
        'user__last_name', 
        'user__employee_id',
        'skill__name'
    ]
    autocomplete_fields = ['user', 'skill']
    date_hierarchy = 'acquired_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'skill', 'proficiency_level')
        }),
        ('Certification', {
            'fields': (
                'is_certified', 
                'certification_date',
                'certification_expiry',
                'certification_authority'
            )
        }),
        ('Tracking', {
            'fields': ('acquired_date', 'last_used_date')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
