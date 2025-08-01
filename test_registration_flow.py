#!/usr/bin/env python
"""
Test script to verify the registration form automatically sets user role to USER
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from apps.accounts.forms import UserRegistrationForm
from apps.teams.models import Team, TeamRole
from apps.accounts.models import Skill

def test_registration_form():
    print("Testing Registration Form Role Assignment")
    print("=" * 50)
    
    # Check if form sets user role to USER automatically
    print("1. Testing that form automatically sets role to USER")
    
    # Get existing data from database
    try:
        # Get existing skills
        waakdienst_skill = Skill.objects.filter(name='Waakdienst', is_active=True).first()
        incident_skill = Skill.objects.filter(name='Incident', is_active=True).first()
        
        if not waakdienst_skill or not incident_skill:
            print("❌ Required skills (Waakdienst, Incident) not found in database")
            return
        
        # Get team role
        team_role = TeamRole.objects.filter(name='operationeel').first()
        if not team_role:
            print("❌ Team role 'operationeel' not found in database")
            return
        
        # Get team
        team = Team.objects.filter(is_active=True).first()
        if not team:
            print("❌ No active teams found in database")
            return
        
        print("✅ Required data found in database")
        
        # Test form data
        form_data = {
            'username': 'test_user_reg',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'testuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'team': team.pk,
            'skills': [waakdienst_skill.pk, incident_skill.pk],
            'team_role': team_role.pk,
        }
        
        form = UserRegistrationForm(data=form_data)
        
        print("2. Form validation:")
        if form.is_valid():
            print("✅ Form is valid")
            
            # Test the save method
            user = form.save(commit=False)
            print(f"3. User role automatically set to: {user.role}")
            
            if user.role == 'USER':
                print("✅ SUCCESS: User role automatically set to USER")
            else:
                print(f"❌ ERROR: User role set to {user.role} instead of USER")
                
        else:
            print("❌ Form validation failed:")
            for field, errors in form.errors.items():
                print(f"  - {field}: {errors}")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("Registration form test completed!")

if __name__ == "__main__":
    test_registration_form()
