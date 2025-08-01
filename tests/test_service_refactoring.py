"""
Test suite for the refactored service layer architecture
Tests the new dashboard service and user service implementations
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from core.services import DashboardService, UserService, PermissionService
from apps.teams.models import Team, TeamMembership
from apps.accounts.models import User, Skill, SkillCategory, UserSkill
from apps.assignments.models import Assignment
from apps.scheduling.models import ShiftTemplate, ShiftInstance, ShiftCategory

User = get_user_model()


class TestDashboardService(TestCase):
    """Test the new dashboard service with strategy pattern"""
    
    def setUp(self):
        """Set up test data"""
        # Create required TeamRole first
        from apps.teams.models import TeamRole
        self.team_role = TeamRole.objects.create(
            name='member',
            description='Team Member'
        )
        
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            role='ADMIN',
            employee_id='A001'
        )
        
        self.manager_user = User.objects.create_user(
            username='manager_test', 
            email='manager@test.com',
            role='MANAGER',
            employee_id='M001'
        )
        
        self.planner_user = User.objects.create_user(
            username='planner_test',
            email='planner@test.com', 
            role='PLANNER',
            employee_id='P001'
        )
        
        self.regular_user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            role='USER', 
            employee_id='U001'
        )
        
        # Create a test team
        self.test_team = Team.objects.create(
            name='Test Team',
            department='IT',
            team_leader=self.manager_user
        )
        
        # Add team memberships
        TeamMembership.objects.create(
            user=self.regular_user,
            team=self.test_team,
            role=self.team_role,
            is_active=True
        )
    
    def test_admin_dashboard_context(self):
        """Test admin dashboard context generation"""
        context = DashboardService.get_dashboard_context(self.admin_user)
        
        self.assertEqual(context['dashboard_type'], 'admin')
        self.assertIn('total_users', context)
        self.assertIn('total_teams', context)
        self.assertIn('system_health', context)
        self.assertIn('recent_activity', context)
        
        # Test that context includes base data
        self.assertIn('today', context)
        self.assertIn('current_time', context)
    
    def test_manager_dashboard_context(self):
        """Test manager dashboard context generation"""
        context = DashboardService.get_dashboard_context(self.manager_user)
        
        self.assertEqual(context['dashboard_type'], 'manager')
        self.assertIn('managed_teams', context)
        self.assertIn('total_managed_teams', context)
        self.assertIn('pending_approvals', context)
        self.assertIn('team_stats', context)
        
        # Verify manager sees their managed teams
        managed_teams = context['managed_teams']
        self.assertEqual(managed_teams.first().id, self.test_team.id)
    
    def test_planner_dashboard_context(self):
        """Test planner dashboard context generation"""
        context = DashboardService.get_dashboard_context(self.planner_user)
        
        self.assertEqual(context['dashboard_type'], 'planner')
        self.assertIn('planning_periods', context)
        self.assertIn('unassigned_shifts', context)
        self.assertIn('planning_advice', context)
        self.assertIn('recent_planning_activity', context)
    
    def test_user_dashboard_context(self):
        """Test regular user dashboard context generation"""
        context = DashboardService.get_dashboard_context(self.regular_user)
        
        self.assertEqual(context['dashboard_type'], 'user')
        self.assertIn('upcoming_shifts', context)
        self.assertIn('my_leave_requests', context)
        self.assertIn('incident_engineer_today', context)
        self.assertIn('waakdienst_engineer_today', context)
        self.assertIn('total_working_today', context)
        self.assertIn('personal_advice', context)
    
    def test_strategy_selection(self):
        """Test that correct strategy is selected for each role"""
        admin_strategy = DashboardService.get_strategy_for_user(self.admin_user)
        manager_strategy = DashboardService.get_strategy_for_user(self.manager_user)
        planner_strategy = DashboardService.get_strategy_for_user(self.planner_user)
        user_strategy = DashboardService.get_strategy_for_user(self.regular_user)
        
        self.assertEqual(admin_strategy.__class__.__name__, 'AdminDashboardStrategy')
        self.assertEqual(manager_strategy.__class__.__name__, 'ManagerDashboardStrategy')
        self.assertEqual(planner_strategy.__class__.__name__, 'PlannerDashboardStrategy')
        self.assertEqual(user_strategy.__class__.__name__, 'UserDashboardStrategy')


class TestUserService(TestCase):
    """Test the new user service"""
    
    def setUp(self):
        """Set up test data"""
        # Create required TeamRole first
        from apps.teams.models import TeamRole
        self.team_role = TeamRole.objects.create(
            name='member',
            description='Team Member'
        )
        
        self.user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            employee_id='T001',
            role='USER'
        )
        
        # Create skill data
        self.skill_category = SkillCategory.objects.create(
            name='Technical',
            description='Technical skills'
        )
        
        self.skill = Skill.objects.create(
            name='Python',
            category=self.skill_category,
            description='Python programming'
        )
        
        self.user_skill = UserSkill.objects.create(
            user=self.user,
            skill=self.skill,
            proficiency_level='intermediate'
        )
        
        # Create team data
        self.team = Team.objects.create(
            name='Development Team',
            department='IT'
        )
        
        TeamMembership.objects.create(
            user=self.user,
            team=self.team,
            role=self.team_role,
            is_active=True
        )
    
    def test_user_profile_data(self):
        """Test user profile data retrieval"""
        user_service = UserService(self.user)
        profile_data = user_service.get_user_profile_data()
        
        self.assertEqual(profile_data['user'], self.user)
        self.assertIn('ytd_stats', profile_data)
        self.assertIn('skills', profile_data)
        self.assertIn('teams', profile_data)
        self.assertIn('role_permissions', profile_data)
        self.assertIn('recent_assignments', profile_data)
        
        # Test skills are included
        skills = profile_data['skills']
        self.assertEqual(skills.first().skill, self.skill)
        
        # Test teams are included 
        teams = profile_data['teams']
        self.assertIn(self.team, teams)
    
    def test_role_permissions(self):
        """Test role permissions calculation"""
        user_service = UserService(self.user)
        permissions = user_service.get_role_permissions(self.user)
        
        self.assertIn('can_access_planning', permissions)
        self.assertIn('can_access_analytics', permissions)
        self.assertIn('can_manage_teams', permissions)
        self.assertIn('is_team_leader', permissions)
        
        # Regular user should not have advanced permissions
        self.assertFalse(permissions['can_access_planning'])
        self.assertFalse(permissions['can_access_analytics'])
        self.assertFalse(permissions['can_manage_teams'])
    
    def test_workload_stats(self):
        """Test workload statistics calculation"""
        user_service = UserService(self.user)
        stats = user_service.get_workload_stats(self.user, period_days=30)
        
        self.assertIn('period_days', stats)
        self.assertIn('total_assignments', stats)
        self.assertIn('total_hours', stats)
        self.assertIn('weekly_assignments', stats)
        self.assertIn('avg_assignments_per_week', stats)
        self.assertIn('avg_hours_per_week', stats)
        
        # With no assignments, stats should be zero
        self.assertEqual(stats['total_assignments'], 0)
        self.assertEqual(stats['total_hours'], 0.0)


class TestPermissionService(TestCase):
    """Test the permission service"""
    
    def setUp(self):
        """Set up test users"""
        self.admin_user = User.objects.create_user(
            username='admin',
            role='ADMIN',
            employee_id='A001'
        )
        
        self.manager_user = User.objects.create_user(
            username='manager',
            role='MANAGER', 
            employee_id='M001'
        )
        
        self.planner_user = User.objects.create_user(
            username='planner',
            role='PLANNER',
            employee_id='P001'
        )
        
        self.user = User.objects.create_user(
            username='user',
            role='USER',
            employee_id='U001'
        )
    
    def test_permission_checks(self):
        """Test various permission checks"""
        # Test planning access
        self.assertTrue(PermissionService.can_access_planning(self.admin_user))
        self.assertTrue(PermissionService.can_access_planning(self.manager_user))
        self.assertTrue(PermissionService.can_access_planning(self.planner_user))
        self.assertFalse(PermissionService.can_access_planning(self.user))
        
        # Test analytics access
        self.assertTrue(PermissionService.can_access_analytics(self.admin_user))
        self.assertTrue(PermissionService.can_access_analytics(self.manager_user))
        self.assertFalse(PermissionService.can_access_analytics(self.planner_user))
        self.assertFalse(PermissionService.can_access_analytics(self.user))
        
        # Test team management
        self.assertTrue(PermissionService.can_manage_teams(self.admin_user))
        self.assertTrue(PermissionService.can_manage_teams(self.manager_user))
        self.assertFalse(PermissionService.can_manage_teams(self.planner_user))
        self.assertFalse(PermissionService.can_manage_teams(self.user))


class TestServiceIntegration(TestCase):
    """Test service layer integration"""
    
    def setUp(self):
        """Set up test data for integration testing"""
        self.user = User.objects.create_user(
            username='integration_test',
            email='integration@test.com',
            role='MANAGER',
            employee_id='I001'
        )
    
    def test_dashboard_service_user_service_integration(self):
        """Test that dashboard service properly integrates with user service"""
        # Get dashboard context
        dashboard_context = DashboardService.get_dashboard_context(self.user)
        
        # Verify context has expected structure
        self.assertIn('dashboard_type', dashboard_context)
        self.assertIn('current_user', dashboard_context)
        
        # Test that user service can work with the same user
        user_service = UserService(self.user)
        profile_data = user_service.get_user_profile_data()
        
        # Both services should work with the same user
        self.assertEqual(dashboard_context['current_user'], self.user)
        self.assertEqual(profile_data['user'], self.user)
    
    def test_permission_service_integration(self):
        """Test permission service integration"""
        # Get permissions
        permissions = PermissionService.can_access_planning(self.user)
        self.assertTrue(permissions)  # Manager should have planning access
        
        # Verify dashboard context respects permissions
        dashboard_context = DashboardService.get_dashboard_context(self.user)
        self.assertEqual(dashboard_context['dashboard_type'], 'manager')
        
        # User service should also provide consistent permissions
        user_service = UserService(self.user)
        profile_data = user_service.get_user_profile_data()
        role_permissions = profile_data['role_permissions']
        
        self.assertTrue(role_permissions['can_access_planning'])
        self.assertTrue(role_permissions['is_manager'])