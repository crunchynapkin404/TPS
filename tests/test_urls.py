#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append('/home/bart/Planner/V1.4/tps_v14')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from django.urls import resolve, reverse
from django.conf.urls import include
from django.test import Client

try:
    print("Testing URL resolution for /api/v1/assignments/overview/")
    
    # Test URL resolution
    match = resolve('/api/v1/assignments/overview/')
    print(f"✅ URL resolves to: {match.func.__name__} in {match.func.__module__}")
    print(f"✅ URL pattern name: {match.url_name}")
    
except Exception as e:
    print(f"❌ URL resolution failed: {e}")

try:
    print("\nTesting reverse URL lookup...")
    url = reverse('assignments-overview')
    print(f"✅ Reverse URL: {url}")
except Exception as e:
    print(f"❌ Reverse URL failed: {e}")

# Test with client
print("\nTesting with Django test client...")
client = Client()
response = client.get('/api/v1/assignments/overview/')
print(f"Response status: {response.status_code}")
if response.status_code == 404:
    print("❌ Still getting 404 - URL not found")
elif response.status_code == 403:
    print("✅ Getting 403 - URL found but needs authentication")
else:
    print(f"Response: {response.content[:200]}")
