"""
TPS V1.4 - API Integration Tests
Tests for API endpoints and basic functionality
"""

from datetime import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.config import config_manager

from apps.teams.models import Team, TeamMembership, TeamRole

User = get_user_model()


class APIIntegrationTest(TestCase):
    """Test API endpoints work correctly"""
    
    def setUp(self):
        """Create minimal test data for API tests"""
        self.client = APIClient()
        
        # Get test configuration
        test_config = config_manager.get_test_config()
        org_config = config_manager.get_organization_config()
        
        # Create admin user for API authentication
        self.admin_user = User.objects.create_user(
            username="admin",
            email=config_manager.generate_test_email("admin"),
            password=test_config['test_password'],
            employee_id=config_manager.generate_employee_id(1, 'ADM'),
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.user = User.objects.create_user(
            username="testuser",
            email=config_manager.generate_test_email("testuser"), 
            password=test_config['test_password'],
            employee_id=config_manager.generate_employee_id(1)
        )
        
        # Create team
        self.team = Team.objects.create(
            name="Test Team",
            description="Integration test team",
            department="Engineering"
        )
    
    def test_api_authentication(self):
        """Test API authentication works"""
        # Test unauthenticated request
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test authenticated request
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_api_endpoints(self):
        """Test user API endpoints"""
        self.client.force_authenticate(user=self.admin_user)
        
        # List users
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # Get specific user
        response = self.client.get(f'/api/v1/users/{self.user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_team_api_endpoints(self):
        """Test team API endpoints"""
        self.client.force_authenticate(user=self.admin_user)
        
        # List teams
        response = self.client.get('/api/v1/teams/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # Get specific team
        response = self.client.get(f'/api/v1/teams/{self.team.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Team')
    
    def test_assignment_api_endpoints(self):
        """Test assignment API endpoints"""
        self.client.force_authenticate(user=self.admin_user)
        
        # List assignments (should be empty initially)
        response = self.client.get('/api/v1/assignments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class SystemHealthTest(TestCase):
    """Test overall system health"""
    
    def test_database_connection(self):
        """Test database operations work"""
        # Create a user
        user = User.objects.create_user(
            username="healthtest",
            email="health@test.com",
            employee_id="HEALTH001"
        )
        
        # Verify user was created
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "healthtest")
        
        # Query users
        users = User.objects.filter(username="healthtest")
        self.assertEqual(users.count(), 1)
    
    def test_user_model_fields(self):
        """Test user model has expected fields"""
        user = User.objects.create_user(
            username="fieldtest",
            email="field@test.com",
            employee_id="FIELD001"
        )
        
        # Test required fields exist
        self.assertTrue(hasattr(user, 'username'))
        self.assertTrue(hasattr(user, 'email'))
        self.assertTrue(hasattr(user, 'employee_id'))
        self.assertTrue(hasattr(user, 'ytd_waakdienst_weeks'))
        self.assertTrue(hasattr(user, 'ytd_incident_weeks'))
        
        # Test default values
        self.assertEqual(user.ytd_waakdienst_weeks, 0)
        self.assertEqual(user.ytd_incident_weeks, 0)
    
    def test_team_model_basic_operations(self):
        """Test team model basic operations"""
        # Create team
        team = Team.objects.create(
            name="Health Test Team",
            description="Health test",
            department="IT"
        )
        
        # Verify team was created
        self.assertIsNotNone(team.id)
        self.assertEqual(team.name, "Health Test Team")
        self.assertTrue(team.is_active)
        
        # Test team methods
        self.assertEqual(team.get_member_count(), 0)
        self.assertTrue(team.can_accommodate_shift(1))


if __name__ == "__main__":
    # Run with Django test runner
    import os
    import django
    from django.test.utils import get_runner
    from django.conf import settings
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests.test_api_integration"])
