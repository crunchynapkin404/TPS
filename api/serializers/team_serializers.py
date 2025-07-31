"""
TPS V1.4 - Team Serializers
Django REST Framework serializers for team management
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamRole, TeamMembership, TeamScheduleTemplate

User = get_user_model()


class TeamRoleSerializer(serializers.ModelSerializer):
    """Serializer for team roles"""
    
    class Meta:
        model = TeamRole
        fields = ['id', 'name', 'description', 'can_assign_shifts', 'can_approve_leave', 'is_leadership']


class TeamMembershipSerializer(serializers.ModelSerializer):
    """Serializer for team membership with user and role information"""
    
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    role = TeamRoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamMembership
        fields = [
            'id', 'user', 'user_id', 'user_full_name', 'role', 'role_id',
            'joined_date', 'is_active', 'notes'
        ]
    
    def get_user_full_name(self, obj):
        """Return full name of team member"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class TeamScheduleTemplateSerializer(serializers.ModelSerializer):
    """Serializer for team schedule templates"""
    
    class Meta:
        model = TeamScheduleTemplate
        fields = [
            'id', 'name', 'description', 'days_of_week', 'start_time',
            'end_time', 'required_staffing', 'is_active'
        ]


class TeamStatisticsSerializer(serializers.Serializer):
    """Serializer for team statistics"""
    
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    completed_assignments_this_month = serializers.IntegerField()
    average_workload_balance = serializers.DecimalField(max_digits=5, decimal_places=2)
    upcoming_shifts_count = serializers.IntegerField()


class TeamWorkloadSerializer(serializers.Serializer):
    """Serializer for team workload analysis"""
    
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    ytd_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    ytd_weeks_waakdienst = serializers.IntegerField()
    ytd_weeks_incident = serializers.IntegerField()
    fairness_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    next_availability = serializers.DateField(allow_null=True)


class TeamScheduleSerializer(serializers.Serializer):
    """Serializer for team schedule data"""
    
    date = serializers.DateField()
    assignments = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    total_shifts = serializers.IntegerField()
    coverage_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class TeamSerializer(serializers.ModelSerializer):
    """Main team serializer with full information"""
    
    team_leader = serializers.StringRelatedField(read_only=True)
    team_leader_id = serializers.IntegerField(write_only=True, required=False)
    memberships = TeamMembershipSerializer(source='memberships', many=True, read_only=True)
    schedule_templates = TeamScheduleTemplateSerializer(many=True, read_only=True)
    statistics = TeamStatisticsSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'name', 'description', 'department', 'location',
            'team_leader', 'team_leader_id', 'min_members_per_shift',
            'max_members_per_shift', 'is_active', 'contact_email',
            'contact_phone', 'memberships', 'schedule_templates',
            'statistics', 'member_count', 'created_at', 'updated_at'
        ]
    
    def get_member_count(self, obj):
        """Return count of active team members"""
        return obj.memberships.filter(is_active=True).count()


class TeamListSerializer(serializers.ModelSerializer):
    """Simplified team serializer for list views"""
    
    team_leader_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'name', 'description', 'department', 'location',
            'team_leader_name', 'member_count', 'is_active'
        ]
    
    def get_team_leader_name(self, obj):
        """Return team leader's full name"""
        if obj.team_leader:
            return f"{obj.team_leader.first_name} {obj.team_leader.last_name}".strip()
        return None
    
    def get_member_count(self, obj):
        """Return count of active team members"""
        return obj.memberships.filter(is_active=True).count()


class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new teams"""
    
    class Meta:
        model = Team
        fields = [
            'name', 'description', 'department', 'location', 'team_leader',
            'min_members_per_shift', 'max_members_per_shift', 'contact_email',
            'contact_phone'
        ]
    
    def validate_name(self, value):
        """Ensure team name is unique within department"""
        department = self.initial_data.get('department')
        if Team.objects.filter(name=value, department=department).exists():
            raise serializers.ValidationError(
                "Team with this name already exists in the department"
            )
        return value


class TeamUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating team information"""
    
    class Meta:
        model = Team
        fields = [
            'description', 'location', 'team_leader', 'min_members_per_shift',
            'max_members_per_shift', 'contact_email', 'contact_phone', 'is_active'
        ]


class AddTeamMemberSerializer(serializers.Serializer):
    """Serializer for adding members to a team"""
    
    user_id = serializers.IntegerField()
    role_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_user_id(self, value):
        """Validate that user exists and is active"""
        try:
            user = User.objects.get(id=value)
            if not user.is_active:
                raise serializers.ValidationError("User is not active")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
    
    def validate_role_id(self, value):
        """Validate that role exists"""
        try:
            TeamRole.objects.get(id=value)
            return value
        except TeamRole.DoesNotExist:
            raise serializers.ValidationError("Team role does not exist")
    
    def validate(self, data):
        """Validate that user is not already a member of the team"""
        team = self.context.get('team')
        user_id = data['user_id']
        
        if team and TeamMembership.objects.filter(
            team=team, user_id=user_id, is_active=True
        ).exists():
            raise serializers.ValidationError("User is already a member of this team")
        
        return data


class TeamPlanningDataSerializer(serializers.Serializer):
    """Serializer for team planning data"""
    
    planning_period_start = serializers.DateField()
    planning_period_end = serializers.DateField()
    total_shifts_needed = serializers.IntegerField()
    total_hours_needed = serializers.DecimalField(max_digits=10, decimal_places=2)
    available_members = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    constraints = serializers.JSONField(required=False)
    recommendations = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
