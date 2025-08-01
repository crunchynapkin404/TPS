"""
Critical tests for TPS User model and authentication
Tests user permissions, role hierarchy, and business logic
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal

@pytest.mark.unit
@pytest.mark.critical
class TestUserModel:
    """Test User model functionality"""
    
    def test_user_creation(self):
        """Test basic user creation"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.employee_id == 'EMP001'
        assert user.role == 'USER'  # Default role
        assert user.is_active_employee is True
    
    def test_employee_id_uniqueness(self):
        """Test employee_id must be unique"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            employee_id='EMP001'
        )
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username='user2',
                email='user2@test.com',
                password='testpass123',
                employee_id='EMP001'  # Duplicate employee_id
            )
    
    def test_ytd_tracking_fields(self):
        """Test year-to-date tracking fields"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001',
            ytd_waakdienst_weeks=5,
            ytd_incident_weeks=8,
            ytd_hours_logged=Decimal('145.50')
        )
        
        assert user.ytd_waakdienst_weeks == 5
        assert user.ytd_incident_weeks == 8
        assert user.ytd_hours_logged == Decimal('145.50')
    
    def test_ytd_limits_validation(self):
        """Test YTD weeks cannot exceed 52"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        
        # Test maximum waakdienst weeks
        user.ytd_waakdienst_weeks = 52
        user.full_clean()  # Should not raise
        
        user.ytd_waakdienst_weeks = 53
        with pytest.raises(ValidationError):
            user.full_clean()
    
    def test_role_hierarchy(self):
        """Test role hierarchy and permissions"""
        # Test each role level
        user_roles = ['USER', 'PLANNER', 'MANAGER', 'ADMIN']
        
        for i, role in enumerate(user_roles):
            user = User.objects.create_user(
                username=f'user_{role.lower()}',
                email=f'{role.lower()}@test.com',
                password='testpass123',
                employee_id=f'{role}_001',
                role=role
            )
            
            # User should have their own role and lower roles
            for j, test_role in enumerate(user_roles):
                if j <= i:
                    assert user.has_role(test_role), f"{role} should have {test_role} role"
                else:
                    assert not user.has_role(test_role), f"{role} should not have {test_role} role"
    
    def test_is_user_property(self):
        """Test is_user property"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001',
            role='USER'
        )
        assert user.is_user is True
        
        admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='testpass123',
            employee_id='ADM001',
            role='ADMIN'
        )
        assert admin.is_user is False
    
    def test_preferences_json_fields(self):
        """Test JSON field handling for preferences"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001',
            preferred_shift_types=['WAAKDIENST', 'INCIDENT'],
            blackout_dates=[
                {'start': '2024-12-20', 'end': '2024-12-31', 'reason': 'Holiday'}
            ]
        )
        
        assert user.preferred_shift_types == ['WAAKDIENST', 'INCIDENT']
        assert len(user.blackout_dates) == 1
        assert user.blackout_dates[0]['reason'] == 'Holiday'
    
    def test_max_consecutive_days_default(self):
        """Test max_consecutive_days has proper default"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001'
        )
        assert user.max_consecutive_days == 7


@pytest.mark.unit
@pytest.mark.critical
class TestUserPermissions:
    """Test user permission system"""
    
    def test_admin_permissions(self, admin_user):
        """Test admin has all permissions"""
        assert admin_user.has_role('USER')
        assert admin_user.has_role('PLANNER')
        assert admin_user.has_role('MANAGER')
        assert admin_user.has_role('ADMIN')
    
    def test_manager_permissions(self, manager_user):
        """Test manager permissions"""
        assert manager_user.has_role('USER')
        assert manager_user.has_role('PLANNER')
        assert manager_user.has_role('MANAGER')
        assert not manager_user.has_role('ADMIN')
    
    def test_planner_permissions(self, planner_user):
        """Test planner permissions"""
        assert planner_user.has_role('USER')
        assert planner_user.has_role('PLANNER')
        assert not planner_user.has_role('MANAGER')
        assert not planner_user.has_role('ADMIN')
    
    def test_user_permissions(self, regular_user):
        """Test regular user permissions"""
        assert regular_user.has_role('USER')
        assert not regular_user.has_role('PLANNER')
        assert not regular_user.has_role('MANAGER')
        assert not regular_user.has_role('ADMIN')
    
    def test_invalid_role_check(self, regular_user):
        """Test checking invalid role raises error"""
        with pytest.raises(ValueError):
            regular_user.has_role('INVALID_ROLE')


@pytest.mark.integration
@pytest.mark.critical 
class TestUserBusinessLogic:
    """Test user-related business logic"""
    
    def test_user_capacity_tracking(self):
        """Test user can track their assignment capacity"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001',
            ytd_waakdienst_weeks=6,
            ytd_incident_weeks=10
        )
        
        # Check against TPS business rules (from settings)
        from django.conf import settings
        tps_config = getattr(settings, 'TPS_CONFIG', {})
        max_waakdienst = tps_config.get('MAX_WAAKDIENST_WEEKS_PER_YEAR', 8)
        max_incident = tps_config.get('MAX_INCIDENT_WEEKS_PER_YEAR', 12)
        
        waakdienst_remaining = max_waakdienst - user.ytd_waakdienst_weeks
        incident_remaining = max_incident - user.ytd_incident_weeks
        
        assert waakdienst_remaining == 2  # 8 - 6 = 2
        assert incident_remaining == 2    # 12 - 10 = 2
    
    def test_user_availability_preferences(self):
        """Test user availability and preferences"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            employee_id='EMP001',
            max_consecutive_days=5,
            preferred_shift_types=['WAAKDIENST'],
            blackout_dates=[
                {
                    'start': '2024-12-20',
                    'end': '2024-12-31',
                    'reason': 'Annual leave'
                }
            ]
        )
        
        # Test preferences are stored correctly
        assert user.max_consecutive_days == 5
        assert 'WAAKDIENST' in user.preferred_shift_types
        assert len(user.blackout_dates) == 1
        
        # Test blackout period
        blackout = user.blackout_dates[0]
        assert blackout['start'] == '2024-12-20'
        assert blackout['end'] == '2024-12-31'
        assert blackout['reason'] == 'Annual leave'