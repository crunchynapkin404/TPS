#!/usr/bin/env python
import requests
import json

# Test Teams API endpoints with authentication
base_url = "http://localhost:8001"

# First, try to login to get session
session = requests.Session()

# Try to get CSRF token
csrf_response = session.get(f"{base_url}/")
csrf_token = None
if 'csrftoken' in session.cookies:
    csrf_token = session.cookies['csrftoken']
    print(f"CSRF Token: {csrf_token}")

# Try login with admin user
login_data = {
    'username': 'admin',
    'password': 'admin',  # common default
    'csrfmiddlewaretoken': csrf_token
}

if csrf_token:
    headers = {'X-CSRFToken': csrf_token, 'Referer': base_url}
    login_response = session.post(f"{base_url}/admin/login/", data=login_data, headers=headers)
    print(f"Login response status: {login_response.status_code}")

# Now test the API endpoints
api_endpoints = [
    "/api/v1/teams/overview/",
    "/api/v1/teams/statistics/",
]

for endpoint in api_endpoints:
    try:
        response = session.get(f"{base_url}{endpoint}")
        print(f"\n{endpoint}:")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
