"""
Simple test configuration for TPS
"""
import pytest


# Test markers
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(db):
    """Create admin user for testing"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        employee_id='ADMIN_001',
        role='ADMIN'
    )


@pytest.fixture
def regular_user(db):
    """Create regular user for testing"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='user_test',
        email='user@test.com',
        password='testpass123',
        employee_id='USR_001',
        role='USER'
    )


@pytest.fixture
def test_team(db):
    """Create test team"""
    from apps.teams.models import Team
    return Team.objects.create(
        name='Test Engineering Team',
        description='Test team for unit tests',
        department='Engineering',
        location='Amsterdam',
        min_members_per_shift=1,
        max_members_per_shift=3,
        preferred_team_size=8,
        is_active=True
    )