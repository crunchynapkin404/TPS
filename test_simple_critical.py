"""
Simple critical tests for TPS User model
"""
import pytest
from decimal import Decimal


@pytest.mark.django_db
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
    
    def test_role_hierarchy(self):
        """Test role hierarchy and permissions"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Test admin role
        admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            employee_id='ADM001',
            role='ADMIN'
        )
        
        assert admin.has_role('USER')
        assert admin.has_role('PLANNER')  
        assert admin.has_role('MANAGER')
        assert admin.has_role('ADMIN')
    
    def test_user_permissions(self):
        """Test regular user permissions"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            employee_id='USR001',
            role='USER'
        )
        
        assert user.has_role('USER')
        assert not user.has_role('PLANNER')
        assert not user.has_role('MANAGER')
        assert not user.has_role('ADMIN')


@pytest.mark.django_db
class TestTeamModel:
    """Test Team model functionality"""
    
    def test_team_creation(self):
        """Test basic team creation"""
        from apps.teams.models import Team
        
        team = Team.objects.create(
            name='Test Team',
            description='Test team',
            department='Engineering',
            location='Amsterdam',
            min_members_per_shift=1,
            max_members_per_shift=3,
            is_active=True
        )
        
        assert team.name == 'Test Team'
        assert team.department == 'Engineering'
        assert team.is_active is True
        assert team.can_accommodate_shift(1) is False  # No members yet, cannot accommodate
    
    def test_team_capacity(self):
        """Test team capacity checking"""
        from apps.teams.models import Team
        
        team = Team.objects.create(
            name='Capacity Test Team',
            department='Engineering',
            min_members_per_shift=1,
            max_members_per_shift=3,
            preferred_team_size=8,
            is_active=True
        )
        
        # Test capacity settings
        assert team.min_members_per_shift == 1
        assert team.max_members_per_shift == 3
        assert team.preferred_team_size == 8