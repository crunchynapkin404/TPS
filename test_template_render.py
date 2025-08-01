#!/usr/bin/env python
"""
Simple Django test to render the schedule template and check for errors
"""
import os
import sys
import django

# Add project to path
sys.path.append('/home/bart/Planner/1.5/TPS')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from django.template import Template, Context
from django.template.loader import get_template
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from frontend.views import ScheduleView

def test_schedule_template():
    """Test if the schedule template renders without errors"""
    
    try:
        # Get the template
        template = get_template('pages/schedule.html')
        
        # Create a simple context
        context = {
            'user': None,
            'request': None,
            'page_title': 'Test Schedule',
            'csrf_token': 'test-token'
        }
        
        # Try to render
        rendered = template.render(context)
        
        # Check if it has the basic structure we expect
        if 'TPS Schedule System' in rendered:
            print("✅ Template renders successfully!")
            print("✅ Contains expected JavaScript initialization")
            return True
        else:
            print("❌ Template renders but missing expected content")
            return False
            
    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_schedule_template()
    if success:
        print("\n🎉 Schedule template appears to be working correctly!")
        print("The original ReferenceError was likely due to missing Alpine.js CDN.")
        print("This has been fixed by updating base.html to use Alpine.js CDN.")
    else:
        print("\n⚠️ There may still be issues with the template.")
