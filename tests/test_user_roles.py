#!/usr/bin/env python
"""
Test script to verify the User model role field functionality
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/home/bart/Planner/V1.4/tps_v14')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def test_user_roles():
    print("Testing User Model Role Functionality")
    print("=" * 50)
    
    # Test role choices
    print("Available role choices:")
    for choice in User.ROLE_CHOICES:
        print(f"  - {choice[0]}: {choice[1]}")
    
    print("\nUser role helper methods test:")
    
    # Create test users with different roles
    test_users = [
        {'username': 'test_user', 'role': 'USER', 'employee_id': 'EMP001'},
        {'username': 'test_planner', 'role': 'PLANNER', 'employee_id': 'EMP002'},
        {'username': 'test_manager', 'role': 'MANAGER', 'employee_id': 'EMP003'},
    ]
    
    for user_data in test_users:
        try:
            # Try to get existing user or create new one
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'role': user_data['role'],
                    'employee_id': user_data['employee_id']
                }
            )
            
            if not created:
                # Update role if user already exists
                user.role = user_data['role']
                user.save()
            
            print(f"\nUser: {user.username}")
            print(f"  Role: {user.role}")
            print(f"  is_planner(): {user.is_planner()}")
            print(f"  is_manager(): {user.is_manager()}")
            print(f"  can_access_planning(): {user.can_access_planning()}")
            
        except Exception as e:
            print(f"Error with user {user_data['username']}: {e}")
    
    print("\n" + "=" * 50)
    print("Role field testing completed!")

if __name__ == "__main__":
    test_user_roles()
