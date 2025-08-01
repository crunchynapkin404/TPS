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
            'assignment_type', 'status', 'assigned_by', 'assigned_by_id', 'assigned_at',
            'confirmed_at', 'completed_at', 'assignment_notes', 'user_notes'
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
            'id', 'user_name', 'shift_name', 'shift_date', 'assignment_type',
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
    
    requesting_assignment = AssignmentListSerializer(read_only=True)
    requesting_assignment_id = serializers.IntegerField(write_only=True)
    target_assignment = AssignmentListSerializer(read_only=True)
    
    # Custom field to handle empty strings and None values
    target_assignment_id = serializers.CharField(
        write_only=True, 
        required=False, 
        allow_blank=True, 
        allow_null=True
    )
    
    requesting_user = serializers.StringRelatedField(read_only=True)
    target_user = serializers.StringRelatedField(read_only=True)
    approved_by = serializers.StringRelatedField(read_only=True)
    
    # Custom datetime field with multiple format support
    expires_at = serializers.DateTimeField(
        input_formats=[
            '%Y-%m-%dT%H:%M',      # HTML datetime-local format
            '%d/%m/%Y %H:%M',      # DD/MM/YYYY format
            '%d/%m/%Y %H:%M:%S',   # DD/MM/YYYY with seconds
            '%d-%m-%Y %H:%M',      # DD-MM-YYYY format
            '%Y-%m-%d %H:%M:%S',   # ISO format with seconds
            '%Y-%m-%d %H:%M',      # ISO format without seconds
        ],
        error_messages={
            'invalid': 'Datetime has wrong format. Use one of these formats instead: DD/MM/YYYY hh:mm, DD/MM/YYYY hh:mm:ss, DD-MM-YYYY hh:mm, YYYY-MM-DD hh:mm:ss.'
        }
    )
    
    class Meta:
        model = SwapRequest
        fields = [
            'id', 'request_id', 'requesting_user', 'requesting_assignment', 'requesting_assignment_id',
            'target_user', 'target_assignment', 'target_assignment_id', 'status', 'swap_type',
            'reason', 'urgency_level', 'requested_at', 'expires_at', 'resolved_at',
            'target_user_approved', 'manager_approved', 'approved_by', 
            'additional_notes', 'resolution_notes'
        ]
        read_only_fields = ['request_id', 'requested_at', 'resolved_at']
    
    def validate_target_assignment_id(self, value):
        """Handle empty string values for target_assignment_id"""
        if value == '' or value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError("A valid integer is required.")
    
    def validate(self, attrs):
        """Custom validation for the entire serializer"""
        # Handle target_assignment_id conversion
        target_id = attrs.get('target_assignment_id')
        if target_id == '' or target_id is None:
            attrs['target_assignment_id'] = None
        elif isinstance(target_id, str):
            try:
                attrs['target_assignment_id'] = int(target_id)
            except (ValueError, TypeError):
                attrs['target_assignment_id'] = None
        
        return attrs


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
    
    def validate(self, attrs):
        """Validate planning request"""
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        
        # Validate date range (maximum 12 weeks)
        date_diff = (attrs['end_date'] - attrs['start_date']).days
        if date_diff > 84:  # 12 weeks
            raise serializers.ValidationError("Planning period cannot exceed 12 weeks")
        
        return attrs


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
