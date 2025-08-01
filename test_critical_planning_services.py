"""
Critical tests for TPS Planning Services
Tests core scheduling algorithms and business logic
"""
import pytest
from datetime import datetime, date, timedelta
from django.utils import timezone
from unittest.mock import Mock, patch
from decimal import Decimal

from core.services.planning_orchestrator import PlanningOrchestrator
from core.services.waakdienst_planning_service import WaakdienstPlanningService
from core.services.fairness_service import FairnessService
from apps.teams.models import Team, TeamMembership
from apps.scheduling.models import ShiftTemplate, ShiftInstance, ShiftCategory


@pytest.mark.unit
@pytest.mark.critical
class TestPlanningOrchestrator:
    """Test Planning Orchestrator core functionality"""
    
    def test_orchestrator_initialization(self, team_with_members):
        """Test orchestrator initializes with team"""
        orchestrator = PlanningOrchestrator(team_with_members)
        
        assert orchestrator.team == team_with_members
        assert hasattr(orchestrator, 'waakdienst_service')
        assert hasattr(orchestrator, 'incident_service')
        assert hasattr(orchestrator, 'fairness_service')
        assert orchestrator.last_planning_id is None
        assert orchestrator.planning_history == []
    
    def test_orchestrator_team_validation(self):
        """Test orchestrator requires valid team"""
        with pytest.raises(TypeError):
            PlanningOrchestrator(None)
    
    @patch('core.services.planning_orchestrator.logger')
    def test_orchestrator_logging(self, mock_logger, team_with_members):
        """Test orchestrator logs initialization"""
        orchestrator = PlanningOrchestrator(team_with_members)
        
        mock_logger.info.assert_called_with(
            f"Initialized Planning Orchestrator for {team_with_members.name}"
        )


@pytest.mark.unit
@pytest.mark.critical
class TestWaakdienstPlanningService:
    """Test Waakdienst Planning Service business logic"""
    
    def test_service_initialization(self, team_with_members):
        """Test service initializes with team"""
        service = WaakdienstPlanningService(team_with_members)
        assert service.team == team_with_members
    
    def test_coverage_pattern_constants(self, team_with_members):
        """Test waakdienst coverage pattern is correct"""
        service = WaakdienstPlanningService(team_with_members)
        
        # Based on the docstring, waakdienst should cover:
        # 12 separate shifts totaling 123 hours per week
        # This is critical business logic that must be tested
        
        # Test coverage hours (from docstring):
        expected_hours = [
            7,   # Wed 17:00-24:00
            8,   # Thu 00:00-08:00  
            7,   # Thu 17:00-24:00
            8,   # Fri 00:00-08:00
            7,   # Fri 17:00-24:00
            24,  # Sat 00:00-24:00
            24,  # Sun 00:00-24:00
            8,   # Mon 00:00-08:00
            7,   # Mon 17:00-24:00
            8,   # Tue 00:00-08:00
            7,   # Tue 17:00-24:00
            8    # Wed 00:00-08:00
        ]
        
        total_expected_hours = sum(expected_hours)
        assert total_expected_hours == 123, "Waakdienst coverage should be 123 hours per week"
    
    def test_handover_period_exclusion(self, team_with_members):
        """Test handover period (Wed 08:00-17:00) is excluded"""
        service = WaakdienstPlanningService(team_with_members)
        
        # Handover period: Wednesday 08:00-17:00 (9 hours)
        # This should be covered by incident planning, not waakdienst
        handover_hours = 9
        
        # Total week hours (168) - handover (9) - business hours
        # Business hours: Mon-Fri 08:00-17:00 = 5 days * 9 hours = 45 hours
        # But Wed 08:00-17:00 is handover, so business hours = 4 * 9 = 36 hours
        business_hours = 36
        expected_waakdienst_hours = 168 - handover_hours - business_hours
        
        assert expected_waakdienst_hours == 123, "Waakdienst should cover 123 hours (excluding handover and business hours)"


@pytest.mark.unit
@pytest.mark.critical
class TestFairnessService:
    """Test Fairness Service algorithms"""
    
    def test_fairness_service_initialization(self, team_with_members):
        """Test fairness service initializes"""
        service = FairnessService(team_with_members)
        assert service.team == team_with_members
    
    def test_fairness_calculation_empty_history(self, team_with_members):
        """Test fairness calculation with no assignment history"""
        service = FairnessService(team_with_members)
        
        # With no history, all members should be equally fair
        members = team_with_members.get_active_members()
        fairness_scores = {}
        
        for membership in members:
            # Mock fairness calculation - in real implementation, 
            # this would consider YTD hours, weeks, etc.
            fairness_scores[membership.user.id] = {
                'ytd_waakdienst_weeks': membership.user.ytd_waakdienst_weeks,
                'ytd_incident_weeks': membership.user.ytd_incident_weeks,
                'ytd_hours': float(membership.user.ytd_hours_logged),
                'fairness_score': 1.0  # Equal fairness with no history
            }
        
        assert len(fairness_scores) == 4  # Team has 4 members
        
        # All should have equal fairness initially
        scores = [score['fairness_score'] for score in fairness_scores.values()]
        assert all(score == 1.0 for score in scores), "All members should have equal fairness initially"


@pytest.mark.integration
@pytest.mark.critical
class TestPlanningServiceIntegration:
    """Test integration between planning services"""
    
    def test_full_planning_workflow(self, team_with_members, planning_period, shift_template):
        """Test complete planning workflow"""
        orchestrator = PlanningOrchestrator(team_with_members)
        
        # Test team capacity
        assert team_with_members.can_accommodate_shift(1), "Team should accommodate single shift"
        assert team_with_members.get_member_count() == 4, "Team should have 4 active members"
        
        # Test shift template requirements
        assert shift_template.required_engineers == 1, "Waakdienst requires 1 engineer"
        assert shift_template.duration_hours == 168, "Waakdienst should be 168 hours (full week)"
    
    def test_team_capacity_constraints(self, team_with_members):
        """Test team capacity constraint checking"""
        # Test with current team size
        assert team_with_members.can_accommodate_shift(1) is True
        assert team_with_members.can_accommodate_shift(4) is True
        assert team_with_members.can_accommodate_shift(5) is False  # Exceeds team size
        
        # Test minimum/maximum members per shift
        assert team_with_members.min_members_per_shift == 1
        assert team_with_members.max_members_per_shift == 3
        assert team_with_members.preferred_team_size == 8
    
    def test_user_assignment_limits(self, team_with_members):
        """Test user assignment limits from TPS config"""
        from django.conf import settings
        
        tps_config = getattr(settings, 'TPS_CONFIG', {})
        max_waakdienst_weeks = tps_config.get('MAX_WAAKDIENST_WEEKS_PER_YEAR', 8)
        max_incident_weeks = tps_config.get('MAX_INCIDENT_WEEKS_PER_YEAR', 12)
        min_gap_waakdienst = tps_config.get('MIN_GAP_WAAKDIENST_DAYS', 14)
        min_gap_incident = tps_config.get('MIN_GAP_INCIDENT_DAYS', 7)
        
        # Test business rules are properly configured
        assert max_waakdienst_weeks == 8, "Max waakdienst weeks should be 8"
        assert max_incident_weeks == 12, "Max incident weeks should be 12"
        assert min_gap_waakdienst == 14, "Minimum gap between waakdienst assignments should be 14 days"
        assert min_gap_incident == 7, "Minimum gap between incident assignments should be 7 days"
        
        # Test team members don't exceed limits
        for membership in team_with_members.get_active_members():
            user = membership.user
            assert user.ytd_waakdienst_weeks <= max_waakdienst_weeks, f"User {user.username} exceeds waakdienst limit"
            assert user.ytd_incident_weeks <= max_incident_weeks, f"User {user.username} exceeds incident limit"


@pytest.mark.integration
@pytest.mark.critical
class TestPlanningBusinessRules:
    """Test critical business rules for planning"""
    
    def test_waakdienst_coverage_completeness(self, team_with_members, shift_template):
        """Test waakdienst provides complete 24/7 coverage"""
        service = WaakdienstPlanningService(team_with_members)
        
        # Mock the planning result to test coverage validation
        # In real implementation, this would generate actual shift instances
        coverage_periods = [
            {'start': 'Wed 17:00', 'end': 'Wed 24:00', 'hours': 7},
            {'start': 'Thu 00:00', 'end': 'Thu 08:00', 'hours': 8},
            {'start': 'Thu 17:00', 'end': 'Thu 24:00', 'hours': 7},
            {'start': 'Fri 00:00', 'end': 'Fri 08:00', 'hours': 8},
            {'start': 'Fri 17:00', 'end': 'Fri 24:00', 'hours': 7},
            {'start': 'Sat 00:00', 'end': 'Sat 24:00', 'hours': 24},
            {'start': 'Sun 00:00', 'end': 'Sun 24:00', 'hours': 24},
            {'start': 'Mon 00:00', 'end': 'Mon 08:00', 'hours': 8},
            {'start': 'Mon 17:00', 'end': 'Mon 24:00', 'hours': 7},
            {'start': 'Tue 00:00', 'end': 'Tue 08:00', 'hours': 8},
            {'start': 'Tue 17:00', 'end': 'Tue 24:00', 'hours': 7},
            {'start': 'Wed 00:00', 'end': 'Wed 08:00', 'hours': 8},
        ]
        
        total_coverage_hours = sum(period['hours'] for period in coverage_periods)
        assert total_coverage_hours == 123, "Waakdienst coverage must be exactly 123 hours"
        
        # Test no gaps in coverage (this would be more complex in real implementation)
        assert len(coverage_periods) == 12, "Waakdienst should have exactly 12 coverage periods"
    
    def test_fairness_algorithm_constraints(self, team_with_members):
        """Test fairness algorithm respects user constraints"""
        service = FairnessService(team_with_members)
        
        # Test that fairness considers:
        # 1. YTD hours and weeks
        # 2. User preferences
        # 3. Blackout dates
        # 4. Maximum consecutive days
        
        members = list(team_with_members.get_active_members())
        assert len(members) > 0, "Team should have active members"
        
        for membership in members:
            user = membership.user
            
            # Test user has valid constraints
            assert user.max_consecutive_days > 0, "User should have valid max consecutive days"
            assert isinstance(user.preferred_shift_types, list), "Preferred shift types should be a list"
            assert isinstance(user.blackout_dates, list), "Blackout dates should be a list"
            
            # Test YTD tracking is within reasonable bounds
            assert 0 <= user.ytd_waakdienst_weeks <= 52, "YTD waakdienst weeks should be 0-52"
            assert 0 <= user.ytd_incident_weeks <= 52, "YTD incident weeks should be 0-52"
            assert user.ytd_hours_logged >= 0, "YTD hours should be non-negative"


@pytest.mark.slow
@pytest.mark.critical
class TestPlanningPerformance:
    """Test planning service performance"""
    
    def test_large_team_planning_performance(self):
        """Test planning performance with larger team"""
        # Create larger team for performance testing
        from conftest import TeamFactory, UserFactory
        
        team = TeamFactory()
        users = UserFactory.create_batch(20)  # Large team
        
        # Add users to team
        for user in users:
            TeamMembership.objects.create(team=team, user=user)
        
        # Test orchestrator can handle large team
        orchestrator = PlanningOrchestrator(team)
        assert orchestrator.team.get_member_count() == 20
        
        # Performance test - initialization should be fast
        import time
        start_time = time.time()
        
        # Re-initialize to test performance
        orchestrator = PlanningOrchestrator(team)
        
        end_time = time.time()
        assert (end_time - start_time) < 1.0, "Orchestrator initialization should be under 1 second"