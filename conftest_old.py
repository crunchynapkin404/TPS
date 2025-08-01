"""
Global test configuration and fixtures for TPS
"""
import pytest
from django.test import Client
from django.utils import timezone
from datetime import datetime, timedelta
import factory

# Django setup
pytest_plugins = ['django_tests']


# Database configuration
@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database"""
    pass


@pytest.fixture
def api_client():
    """Authenticated API client"""
    return Client()


@pytest.fixture
def admin_user():
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
def manager_user():
    """Create manager user for testing"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='manager_test',
        email='manager@test.com',
        password='testpass123',
        employee_id='MGR_001',
        role='MANAGER'
    )


@pytest.fixture
def planner_user():
    """Create planner user for testing"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='planner_test',
        email='planner@test.com',
        password='testpass123',
        employee_id='PLN_001',
        role='PLANNER'
    )


@pytest.fixture
def regular_user():
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
def test_team():
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


@pytest.fixture
def team_with_members(test_team, admin_user, manager_user, planner_user, regular_user):
    """Create team with multiple members"""
    from apps.teams.models import TeamMembership
    
    # Add users to team
    TeamMembership.objects.create(team=test_team, user=admin_user, role='TEAM_LEADER')
    TeamMembership.objects.create(team=test_team, user=manager_user, role='SENIOR_ENGINEER')
    TeamMembership.objects.create(team=test_team, user=planner_user, role='ENGINEER')
    TeamMembership.objects.create(team=test_team, user=regular_user, role='ENGINEER')
    
    return test_team


@pytest.fixture
def planning_period():
    """Create test planning period"""
    from apps.scheduling.models import PlanningPeriod
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=7)
    
    return PlanningPeriod.objects.create(
        name=f'Test Period {start_date}',
        start_date=start_date,
        end_date=end_date,
        status='DRAFT',
        is_active=True
    )


@pytest.fixture
def shift_template():
    """Create test shift template"""
    from apps.scheduling.models import ShiftTemplate, ShiftCategory
    
    category, _ = ShiftCategory.objects.get_or_create(
        name='Waakdienst',
        defaults={'description': 'On-call duty'}
    )
    
    return ShiftTemplate.objects.create(
        name='Weekly Waakdienst',
        category=category,
        duration_hours=168,  # Full week
        required_engineers=1,
        description='Weekly on-call duty coverage',
        is_active=True
    )


# Factory classes for complex test data
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'accounts.User'
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    employee_id = factory.Sequence(lambda n: f'EMP{n:03d}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = 'USER'
    is_active = True
    is_active_employee = True


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'teams.Team'
    
    name = factory.Faker('company')
    description = factory.Faker('text', max_nb_chars=200)
    department = factory.Faker('random_element', elements=['Engineering', 'Support', 'Operations'])
    location = 'Amsterdam'
    min_members_per_shift = 1
    max_members_per_shift = 3
    preferred_team_size = 8
    is_active = True


# Test markers
pytestmark = pytest.mark.django_db