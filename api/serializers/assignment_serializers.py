"""
TPS V1.4 - Assignment and Scheduling Serializers
Django REST Framework serializers for assignments and shift scheduling
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.assignments.models import Assignment, AssignmentHistory, SwapRequest
from apps.scheduling.models import ShiftTemplate, ShiftInstance, PlanningPeriod

User = get_user_model()


class ShiftTemplateSerializer(serializers.ModelSerializer):
    """Serializer for shift templates"""
    
    required_skills = serializers.StringRelatedField(many=True, read_only=True)
    required_skill_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ShiftTemplate
        fields = [
            'id', 'name', 'category', 'description', 'duration',
            'required_skills', 'required_skill_ids', 'staffing_requirements',
            'business_hours_only', 'requires_handover', 'color',
            'is_active'
        ]


class ShiftInstanceSerializer(serializers.ModelSerializer):
    """Serializer for shift instances with assignment information"""
    
    template = ShiftTemplateSerializer(read_only=True)
    template_id = serializers.IntegerField(write_only=True)
    assignments = serializers.SerializerMethodField()
    team = serializers.StringRelatedField(read_only=True)
    team_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ShiftInstance
        fields = [
            'id', 'template', 'template_id', 'date', 'start_time', 'end_time',
            'team', 'team_id', 'location', 'notes', 'status', 'assignments',
            'created_at', 'updated_at'
        ]
    
    def get_assignments(self, obj):
        """Return assignment information for this shift"""
        assignments = obj.assignment_set.select_related('user').all()
        return AssignmentListSerializer(assignments, many=True).data


class AssignmentSerializer(serializers.ModelSerializer):
    """Main assignment serializer with full information"""
    
    shift = ShiftInstanceSerializer(read_only=True)
    shift_id = serializers.IntegerField(write_only=True)
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    assigned_by = serializers.StringRelatedField(read_only=True)
    assigned_by_id = serializers.IntegerField(write_only=True, required=False)
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'shift', 'shift_id', 'user', 'user_id', 'user_full_name',
            'role', 'status', 'assigned_by', 'assigned_by_id', 'assigned_at',
            'confirmed_at', 'completed_at', 'notes', 'performance_rating'
        ]
        read_only_fields = ['assigned_at']
    
    def get_user_full_name(self, obj):
        """Return full name of assigned user"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class AssignmentListSerializer(serializers.ModelSerializer):
    """Simplified assignment serializer for list views"""
    
    user_name = serializers.SerializerMethodField()
    shift_name = serializers.SerializerMethodField()
    shift_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'user_name', 'shift_name', 'shift_date', 'role',
            'status', 'assigned_at'
        ]
    
    def get_user_name(self, obj):
        """Return assigned user's full name"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_shift_name(self, obj):
        """Return shift template name"""
        return obj.shift.template.name
    
    def get_shift_date(self, obj):
        """Return shift date"""
        return obj.shift.date


class AssignmentHistorySerializer(serializers.ModelSerializer):
    """Serializer for assignment history/audit trail"""
    
    assignment = AssignmentListSerializer(read_only=True)
    changed_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = AssignmentHistory
        fields = [
            'id', 'assignment', 'action', 'old_values', 'new_values',
            'changed_by', 'changed_at', 'reason'
        ]


class SwapRequestSerializer(serializers.ModelSerializer):
    """Serializer for shift swap requests"""
    
    from_assignment = AssignmentListSerializer(read_only=True)
    from_assignment_id = serializers.IntegerField(write_only=True)
    to_assignment = AssignmentListSerializer(read_only=True)
    to_assignment_id = serializers.IntegerField(write_only=True)
    requested_by = serializers.StringRelatedField(read_only=True)
    approved_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = SwapRequest
        fields = [
            'id', 'from_assignment', 'from_assignment_id', 'to_assignment',
            'to_assignment_id', 'reason', 'status', 'requested_by',
            'requested_at', 'approved_by', 'approved_at', 'rejection_reason'
        ]
        read_only_fields = ['requested_at', 'approved_at']


class BulkAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk assignment operations"""
    
    assignments = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    assigned_by_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_assignments(self, value):
        """Validate assignment data"""
        for assignment_data in value:
            if 'shift_id' not in assignment_data or 'user_id' not in assignment_data:
                raise serializers.ValidationError(
                    "Each assignment must include shift_id and user_id"
                )
        return value


class PlanningPeriodSerializer(serializers.ModelSerializer):
    """Serializer for planning periods"""
    
    team = serializers.StringRelatedField(read_only=True)
    team_id = serializers.IntegerField(write_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PlanningPeriod
        fields = [
            'id', 'name', 'team', 'team_id', 'start_date', 'end_date',
            'status', 'algorithm_used', 'configuration', 'results',
            'created_by', 'created_at', 'applied_at'
        ]
        read_only_fields = ['created_at', 'applied_at']


class PlanningRequestSerializer(serializers.Serializer):
    """Serializer for planning generation requests"""
    
    team_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    algorithm = serializers.ChoiceField(
        choices=[
            ('balanced', 'Balanced Distribution'),
            ('sequential', 'Sequential Assignment'),
            ('custom', 'Custom Rules')
        ]
    )
    preview_only = serializers.BooleanField(default=False)
    configuration = serializers.JSONField(required=False)
    
    def validate(self, data):
        """Validate planning request"""
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        
        # Validate date range (maximum 12 weeks)
        date_diff = (data['end_date'] - data['start_date']).days
        if date_diff > 84:  # 12 weeks
            raise serializers.ValidationError("Planning period cannot exceed 12 weeks")
        
        return data


class PlanningResultSerializer(serializers.Serializer):
    """Serializer for planning generation results"""
    
    planning_period_id = serializers.IntegerField(allow_null=True)
    success = serializers.BooleanField()
    total_shifts = serializers.IntegerField()
    assigned_shifts = serializers.IntegerField()
    unassigned_shifts = serializers.IntegerField()
    coverage_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    fairness_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    assignments = AssignmentListSerializer(many=True, required=False)
    conflicts = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    recommendations = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class ShiftAvailabilitySerializer(serializers.Serializer):
    """Serializer for shift availability data"""
    
    shift_id = serializers.IntegerField()
    available_users = serializers.ListField(
        child=serializers.DictField()
    )
    qualified_users = serializers.ListField(
        child=serializers.DictField()
    )
    recommendations = serializers.ListField(
        child=serializers.DictField()
    )
