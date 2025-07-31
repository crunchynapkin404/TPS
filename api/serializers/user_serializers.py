"""
TPS V1.4 - User and Accounts Serializers
Django REST Framework serializers for user management
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import Skill, UserSkill, SkillCategory

User = get_user_model()


class SkillCategorySerializer(serializers.ModelSerializer):
    """Serializer for skill categories"""
    
    class Meta:
        model = SkillCategory
        fields = ['id', 'name', 'description', 'color', 'is_active']


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for skills with category information"""
    
    category = SkillCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'description', 'category', 'category_id',
            'required_certifications', 'expiry_period_months', 'is_active'
        ]


class UserSkillSerializer(serializers.ModelSerializer):
    """Serializer for user skills with proficiency and certification"""
    
    skill = SkillSerializer(read_only=True)
    skill_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserSkill
        fields = [
            'id', 'skill', 'skill_id', 'proficiency_level', 
            'certified_date', 'expiry_date', 'notes'
        ]


class UserStatisticsSerializer(serializers.Serializer):
    """Serializer for user YTD statistics"""
    
    ytd_hours_worked = serializers.DecimalField(max_digits=10, decimal_places=2)
    ytd_weeks_waakdienst = serializers.IntegerField()
    ytd_weeks_incident = serializers.IntegerField()
    ytd_assignments_completed = serializers.IntegerField()
    ytd_assignments_cancelled = serializers.IntegerField()
    average_performance_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    fairness_score = serializers.DecimalField(max_digits=5, decimal_places=2)


class UserScheduleSerializer(serializers.Serializer):
    """Serializer for user schedule data"""
    
    date = serializers.DateField()
    shift_type = serializers.CharField()
    shift_name = serializers.CharField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    location = serializers.CharField()
    status = serializers.CharField()
    assignment_id = serializers.IntegerField()


class UserPreferencesSerializer(serializers.Serializer):
    """Serializer for user shift preferences"""
    
    preferred_shift_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    availability_constraints = serializers.JSONField(required=False)
    notification_preferences = serializers.JSONField(required=False)
    overtime_availability = serializers.BooleanField(required=False)


class UserSerializer(serializers.ModelSerializer):
    """Main user serializer with full profile information"""
    
    skills = UserSkillSerializer(source='userskill_set', many=True, read_only=True)
    statistics = UserStatisticsSerializer(read_only=True)
    preferences = UserPreferencesSerializer(source='shift_preferences', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'employee_id', 'department', 'role', 'hire_date', 'location',
            'phone_number', 'emergency_contact_name', 'emergency_contact_phone',
            'is_active', 'skills', 'statistics', 'preferences',
            'ytd_hours_worked', 'ytd_weeks_waakdienst', 'ytd_weeks_incident',
            'last_waakdienst_date', 'last_incident_date', 'performance_rating'
        ]
        read_only_fields = [
            'id', 'username', 'ytd_hours_worked', 'ytd_weeks_waakdienst',
            'ytd_weeks_incident', 'last_waakdienst_date', 'last_incident_date'
        ]
    
    def get_full_name(self, obj):
        """Return full name of user"""
        return f"{obj.first_name} {obj.last_name}".strip()


class UserListSerializer(serializers.ModelSerializer):
    """Simplified user serializer for list views"""
    
    full_name = serializers.SerializerMethodField()
    primary_skills = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'employee_id', 'department',
            'role', 'is_active', 'primary_skills', 'ytd_hours_worked'
        ]
    
    def get_full_name(self, obj):
        """Return full name of user"""
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_primary_skills(self, obj):
        """Return list of primary skills for user"""
        return list(
            obj.userskill_set.filter(
                proficiency_level__gte=3  # Proficient or above
            ).values_list('skill__name', flat=True)[:5]
        )


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password',
            'password_confirm', 'employee_id', 'department', 'role',
            'hire_date', 'location', 'phone_number', 'emergency_contact_name',
            'emergency_contact_phone'
        ]
    
    def validate(self, data):
        """Validate password confirmation and employee_id uniqueness"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Check employee_id uniqueness
        if User.objects.filter(employee_id=data['employee_id']).exists():
            raise serializers.ValidationError("Employee ID already exists")
        
        return data
    
    def create(self, validated_data):
        """Create user with proper password hashing"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'department', 'location',
            'phone_number', 'emergency_contact_name', 'emergency_contact_phone',
            'shift_preferences'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change requests"""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, data):
        """Validate password change request"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match")
        
        return data
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        
        return value
