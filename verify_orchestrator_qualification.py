#!/usr/bin/env python
"""
Verification script to check if users are properly qualified for orchestrator
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.accounts.models import UserSkill
from apps.teams.models import Team
from core.services.planning_orchestrator import PlanningOrchestrator

User = get_user_model()

def verify_orchestrator_qualification():
    print("Verifying Orchestrator User Qualification")
    print("=" * 50)
    
    # Check user10 (mand demand)
    try:
        user = User.objects.get(username='user10')
        print(f"✅ Found user: {user.username} ({user.first_name} {user.last_name})")
        
        # Check skills
        user_skills = UserSkill.objects.filter(user=user)
        print(f"User skills:")
        for skill in user_skills:
            print(f"  - {skill.skill.name}: {skill.proficiency_level}")
        
        # Check team
        team = Team.objects.get(name='TPS Beta Team')
        print(f"✅ Team: {team.name}")
        
        # Test orchestrator
        orchestrator = PlanningOrchestrator(team)
        
        # Check if user is in qualified lists
        waakdienst_qualified = user in orchestrator.waakdienst_service.qualified_engineers
        incident_qualified = user in orchestrator.incident_service.qualified_engineers
        
        print(f"✅ Qualified for Waakdienst: {waakdienst_qualified}")
        print(f"✅ Qualified for Incident: {incident_qualified}")
        
        # Check validation
        validation = orchestrator.validate_prerequisites()
        print(f"Orchestrator validation: {'✅ PASSED' if validation.success else '⚠️  FAILED'}")
        if validation.errors:
            print("Validation errors:")
            for error in validation.errors:
                print(f"  - {error}")
        if validation.warnings:
            print("Validation warnings:")
            for warning in validation.warnings:
                print(f"  - {warning}")
        
        print("\n" + "=" * 50)
        if waakdienst_qualified and incident_qualified:
            print("🎉 SUCCESS: User is properly qualified for orchestrator assignments!")
        else:
            print("❌ FAILED: User is not properly qualified")
            
    except User.DoesNotExist:
        print("❌ User 'user10' (mand demand) not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_orchestrator_qualification()
