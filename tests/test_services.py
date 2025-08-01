"""
TPS V1.4 - Simplified Integration Tests
Tests for core functionality with actual service interfaces
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.teams.models import Team, TeamMembership, TeamRole
from apps.scheduling.models import ShiftCategory, ShiftTemplate, ShiftInstance, PlanningPeriod
from apps.assignments.models import Assignment
from apps.accounts.models import SkillCategory, Skill, UserSkill
from apps.leave_management.models import LeaveType, LeaveRequest

from core.services.fairness_service import FairnessService
from core.services.assignment_service import AssignmentService
from core.services.skills_service import SkillsService
from core.services.validation_service import ValidationService
from core.services.planning_orchestrator import PlanningOrchestrator
from core.config import config_manager

User = get_user_model()


class IntegrationTestCase(TestCase):
    """Base integration test case with common setup"""
    
    def setUp(self):
        """Create test data for integration tests"""
        # Create test team
        self.team = Team.objects.create(
            name="Integration Test Team",
            description="Team for integration testing"
        )
        
        # Create test users using configuration
        self.user1 = User.objects.create_user(
            username="testuser1",
            email=config_manager.generate_test_email("testuser1"),
            first_name="John", 
            last_name="Doe",
            employee_id=config_manager.generate_employee_id(1)
        )
        self.user2 = User.objects.create_user(
            username="testuser2",
            email=config_manager.generate_test_email("testuser2"),
            first_name="Jane",
            last_name="Smith",
            employee_id=config_manager.generate_employee_id(2)
        )
        
        # Create team role and memberships
        self.engineer_role, created = TeamRole.objects.get_or_create(
            name="member",
            defaults={
                "description": "Team member role",
                "can_assign_shifts": False,
                "can_approve_swaps": False,
                "can_manage_team": False
            }
        )
        
        TeamMembership.objects.create(
            team=self.team,
            user=self.user1,
            role=self.engineer_role,
            is_active=True
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user2,
            role=self.engineer_role,
            is_active=True
        )
        
        # Create shift category
        self.waakdienst_category = ShiftCategory.objects.create(
            name="WAAKDIENST",
            display_name="24/7 On-call Coverage",
            description="Waakdienst shifts",
            hours_per_week=168,
            max_weeks_per_year=8,
            min_gap_days=14
        )
        
        # Create shift template
        self.waakdienst_template = ShiftTemplate.objects.create(
            name="Waakdienst Week",
            category=self.waakdienst_category,
            description="Weekly waakdienst shift",
            start_time="08:00:00",
            end_time="08:00:00",
            duration_hours=168,
            required_skills=["waakdienst_certified"]
        )
        
        # Create planning period
        self.planning_period = PlanningPeriod.objects.create(
            name="Test Planning Period",
            start_date=datetime(2025, 1, 1).date(),
            end_date=datetime(2025, 3, 31).date(),
            team=self.team
        )


class ServiceInitializationTest(IntegrationTestCase):
    """Test that all services can be initialized properly"""
    
    def test_fairness_service_initialization(self):
        """Test FairnessService can be initialized"""
        service = FairnessService(self.team)
        self.assertIsNotNone(service)
        self.assertEqual(service.team, self.team)
    
    def test_assignment_service_initialization(self):
        """Test AssignmentService can be initialized"""
        service = AssignmentService(self.team)
        self.assertIsNotNone(service)
        self.assertEqual(service.team, self.team)
    
    def test_skills_service_initialization(self):
        """Test SkillsService can be initialized"""
        service = SkillsService(self.team)
        self.assertIsNotNone(service)
        self.assertEqual(service.team, self.team)
    
    def test_validation_service_initialization(self):
        """Test ValidationService can be initialized"""
        service = ValidationService()
        self.assertIsNotNone(service)
    
    def test_planning_orchestrator_initialization(self):
        """Test PlanningOrchestrator can be initialized"""
        orchestrator = PlanningOrchestrator(self.team)
        self.assertIsNotNone(orchestrator)
        self.assertEqual(orchestrator.team, self.team)


class FairnessServiceIntegrationTest(IntegrationTestCase):
    """Test fairness service integration"""
    
    def setUp(self):
        super().setUp()
        self.fairness_service = FairnessService(self.team)
    
    def test_fairness_score_calculation(self):
        """Test basic fairness score calculation"""
        # Create a shift instance
        shift_instance = ShiftInstance.objects.create(
            template=self.waakdienst_template,
            start_datetime=datetime(2025, 1, 8, 8, 0),
            end_datetime=datetime(2025, 1, 15, 8, 0),
            status="PLANNED"
        )
        
        # Calculate fairness score
        score = self.fairness_service.calculate_fairness_score(
            self.user1, shift_instance,
            self.planning_period.start_date,
            self.planning_period.end_date
        )
        
        # Verify score is calculated
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)


class DatabaseConnectivityTest(IntegrationTestCase):
    """Test database operations work correctly"""
    
    def test_user_creation_and_retrieval(self):
        """Test users can be created and retrieved"""
        users = User.objects.filter(username__startswith="testuser")
        self.assertEqual(users.count(), 2)
        
        user1 = User.objects.get(username="testuser1")
        self.assertEqual(user1.first_name, "John")
    
    def test_team_membership_queries(self):
        """Test team membership queries work"""
        members = TeamMembership.objects.filter(team=self.team, is_active=True)
        self.assertEqual(members.count(), 2)
        
        member_users = [m.user for m in members]
        self.assertIn(self.user1, member_users)
        self.assertIn(self.user2, member_users)
    
    def test_shift_template_creation(self):
        """Test shift templates can be created"""
        templates = ShiftTemplate.objects.filter(team=self.team)
        self.assertEqual(templates.count(), 1)
        
        template = templates.first()
        self.assertEqual(template.name, "Waakdienst Week")
        self.assertEqual(template.duration_hours, 168)


class ShiftInstanceCreationTest(IntegrationTestCase):
    """Test shift instances can be created and managed"""
    
    def test_shift_instance_creation(self):
        """Test creating shift instances"""
        shift = ShiftInstance.objects.create(
            template=self.waakdienst_template,
            start_datetime=datetime(2025, 1, 8, 8, 0),
            end_datetime=datetime(2025, 1, 15, 8, 0),
            status="PLANNED"
        )
        
        self.assertIsNotNone(shift.id)
        self.assertEqual(shift.template, self.waakdienst_template)
        self.assertEqual(shift.status, "PLANNED")
    
    def test_assignment_creation(self):
        """Test creating assignments"""
        shift = ShiftInstance.objects.create(
            template=self.waakdienst_template,
            start_datetime=datetime(2025, 1, 8, 8, 0),
            end_datetime=datetime(2025, 1, 15, 8, 0),
            status="PLANNED"
        )
        
        assignment = Assignment.objects.create(
            shift_instance=shift,
            user=self.user1,
            status="PENDING"
        )
        
        self.assertIsNotNone(assignment.id)
        self.assertEqual(assignment.user, self.user1)
        self.assertEqual(assignment.shift_instance, shift)


class SkillsIntegrationTest(IntegrationTestCase):
    """Test skills system integration"""
    
    def setUp(self):
        super().setUp()
        # Create skill category and skills
        self.skill_category = SkillCategory.objects.create(
            name="Technical Skills",
            description="Engineering skills"
        )
        
        self.waakdienst_skill = Skill.objects.create(
            name="waakdienst_certified",
            category=self.skill_category,
            description="Waakdienst certification"
        )
        
        # Assign skill to user1
        UserSkill.objects.create(
            user=self.user1,
            skill=self.waakdienst_skill,
            proficiency_level="EXPERT"
        )
    
    def test_user_skills_query(self):
        """Test querying user skills"""
        user_skills = UserSkill.objects.filter(user=self.user1)
        self.assertEqual(user_skills.count(), 1)
        
        skill = user_skills.first()
        self.assertEqual(skill.skill.name, "waakdienst_certified")
        self.assertEqual(skill.proficiency_level, "EXPERT")
    
    def test_skills_service_team_members(self):
        """Test skills service can access team members"""
        skills_service = SkillsService(self.team)
        
        # Get qualified users for waakdienst template
        qualified_users = skills_service.get_qualified_users(self.waakdienst_template)
        
        # Should return some users (even if skills matching is limited)
        self.assertIsInstance(qualified_users, type(User.objects.all()))


class SystemHealthTest(IntegrationTestCase):
    """Test overall system health and integration"""
    
    def test_all_services_can_be_initialized_together(self):
        """Test all services can coexist"""
        fairness = FairnessService(self.team)
        assignment = AssignmentService(self.team) 
        skills = SkillsService(self.team)
        validation = ValidationService()
        orchestrator = PlanningOrchestrator(self.team)
        
        # All should be initialized without errors
        self.assertIsNotNone(fairness)
        self.assertIsNotNone(assignment)
        self.assertIsNotNone(skills)
        self.assertIsNotNone(validation)
        self.assertIsNotNone(orchestrator)
    
    def test_database_models_have_expected_fields(self):
        """Test model fields are accessible"""
        # Test User model
        self.assertTrue(hasattr(self.user1, 'username'))
        self.assertTrue(hasattr(self.user1, 'email'))
        
        # Test Team model
        self.assertTrue(hasattr(self.team, 'name'))
        self.assertTrue(hasattr(self.team, 'description'))
        
        # Test ShiftTemplate model
        self.assertTrue(hasattr(self.waakdienst_template, 'name'))
        self.assertTrue(hasattr(self.waakdienst_template, 'duration_hours'))
    
    def test_planning_period_date_handling(self):
        """Test date handling in planning periods"""
        period = self.planning_period
        
        # Test date fields
        self.assertIsNotNone(period.start_date)
        self.assertIsNotNone(period.end_date)
        
        # Test date comparison
        self.assertLess(period.start_date, period.end_date)
        
        # Test date arithmetic
        duration = period.end_date - period.start_date
        self.assertGreater(duration.days, 0)



