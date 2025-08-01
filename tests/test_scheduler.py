#!/usr/bin/env python3
"""
TPS Monthly Timeline Shift Scheduler - Comprehensive Test Suite
Tests all API endpoints and database functionality
"""

import requests
import json
from datetime import datetime, date
import time

# Configuration
API_BASE = "http://localhost:8000"
TEST_DATE = "2024-08-15"

def print_test_result(test_name, success, message=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

def test_api_health():
    """Test API health endpoint"""
    try:
        response = requests.get(f"{API_BASE}/api/health")
        success = response.status_code == 200 and response.json().get("status") == "healthy"
        print_test_result("API Health Check", success)
        return success
    except Exception as e:
        print_test_result("API Health Check", False, str(e))
        return False

def test_get_users():
    """Test getting all users"""
    try:
        response = requests.get(f"{API_BASE}/api/users")
        users = response.json()
        success = response.status_code == 200 and len(users) > 0
        print_test_result("Get Users", success, f"Found {len(users)} users")
        return success, users
    except Exception as e:
        print_test_result("Get Users", False, str(e))
        return False, []

def test_get_shift_types():
    """Test getting all shift types"""
    try:
        response = requests.get(f"{API_BASE}/api/shift-types")
        shift_types = response.json()
        success = response.status_code == 200 and len(shift_types) > 0
        print_test_result("Get Shift Types", success, f"Found {len(shift_types)} shift types")
        return success, shift_types
    except Exception as e:
        print_test_result("Get Shift Types", False, str(e))
        return False, []

def test_create_shift(users, shift_types):
    """Test creating a new shift"""
    try:
        shift_data = {
            "user_id": users[0]["id"],
            "shift_type_id": shift_types[0]["id"],
            "date": TEST_DATE,
            "start_time": "09:00",
            "end_time": "17:00",
            "status": "scheduled",
            "notes": "Test shift created by test suite"
        }
        
        response = requests.post(f"{API_BASE}/api/shifts", json=shift_data)
        shift = response.json()
        success = response.status_code == 200 and "id" in shift
        print_test_result("Create Shift", success, f"Created shift ID: {shift.get('id', 'N/A')}")
        return success, shift
    except Exception as e:
        print_test_result("Create Shift", False, str(e))
        return False, {}

def test_update_shift(shift):
    """Test updating an existing shift"""
    try:
        if not shift or "id" not in shift:
            print_test_result("Update Shift", False, "No shift to update")
            return False
            
        update_data = {
            "notes": "Updated by test suite at " + datetime.now().isoformat(),
            "status": "confirmed"
        }
        
        response = requests.put(f"{API_BASE}/api/shifts/{shift['id']}", json=update_data)
        updated_shift = response.json()
        success = response.status_code == 200 and updated_shift.get("status") == "confirmed"
        print_test_result("Update Shift", success, f"Updated shift {shift['id']}")
        return success
    except Exception as e:
        print_test_result("Update Shift", False, str(e))
        return False

def test_get_schedule():
    """Test getting monthly schedule"""
    try:
        response = requests.get(f"{API_BASE}/api/schedule/2024/8")
        schedule = response.json()
        success = (response.status_code == 200 and 
                  "shifts" in schedule and 
                  "users" in schedule and 
                  "shift_types" in schedule)
        shift_count = len(schedule.get("shifts", []))
        print_test_result("Get Schedule", success, f"Schedule has {shift_count} shifts")
        return success
    except Exception as e:
        print_test_result("Get Schedule", False, str(e))
        return False

def test_bulk_operations(users, shift_types):
    """Test bulk shift creation"""
    try:
        shifts_data = []
        for i in range(3):
            shifts_data.append({
                "user_id": users[i % len(users)]["id"],
                "shift_type_id": shift_types[i % len(shift_types)]["id"],
                "date": f"2024-08-{20 + i}",
                "start_time": "10:00",
                "end_time": "18:00",
                "status": "scheduled",
                "notes": f"Bulk test shift {i + 1}"
            })
        
        bulk_data = {"shifts": shifts_data}
        response = requests.post(f"{API_BASE}/api/shifts/bulk", json=bulk_data)
        created_shifts = response.json()
        success = response.status_code == 200 and len(created_shifts) == 3
        print_test_result("Bulk Create Shifts", success, f"Created {len(created_shifts)} shifts")
        return success, created_shifts
    except Exception as e:
        print_test_result("Bulk Create Shifts", False, str(e))
        return False, []

def test_delete_shift(shift):
    """Test deleting a shift"""
    try:
        if not shift or "id" not in shift:
            print_test_result("Delete Shift", False, "No shift to delete")
            return False
            
        response = requests.delete(f"{API_BASE}/api/shifts/{shift['id']}")
        success = response.status_code == 200
        print_test_result("Delete Shift", success, f"Deleted shift {shift['id']}")
        return success
    except Exception as e:
        print_test_result("Delete Shift", False, str(e))
        return False

def test_api_performance():
    """Test API response times"""
    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE}/api/schedule/2024/8")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        success = response.status_code == 200 and response_time < 1000  # Under 1 second
        print_test_result("API Performance", success, f"Response time: {response_time:.2f}ms")
        return success
    except Exception as e:
        print_test_result("API Performance", False, str(e))
        return False

def main():
    """Run comprehensive test suite"""
    print("🧪 TPS Monthly Timeline Shift Scheduler - Test Suite\n")
    
    # Track test results
    test_results = []
    
    # Test 1: API Health
    test_results.append(test_api_health())
    
    # Test 2: Get Users
    success, users = test_get_users()
    test_results.append(success)
    
    # Test 3: Get Shift Types
    success, shift_types = test_get_shift_types()
    test_results.append(success)
    
    # Test 4: Create Shift
    success, created_shift = test_create_shift(users, shift_types)
    test_results.append(success)
    
    # Test 5: Update Shift
    test_results.append(test_update_shift(created_shift))
    
    # Test 6: Get Schedule
    test_results.append(test_get_schedule())
    
    # Test 7: Bulk Operations
    success, bulk_shifts = test_bulk_operations(users, shift_types)
    test_results.append(success)
    
    # Test 8: API Performance
    test_results.append(test_api_performance())
    
    # Test 9: Delete Shift (cleanup)
    if created_shift:
        test_results.append(test_delete_shift(created_shift))
    
    # Clean up bulk shifts
    if bulk_shifts:
        for shift in bulk_shifts[:2]:  # Keep one for demonstration
            requests.delete(f"{API_BASE}/api/shifts/{shift['id']}")
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 All tests passed! The API is fully functional.")
    elif success_rate >= 80:
        print("⚠️  Most tests passed. Minor issues detected.")
    else:
        print("❌ Multiple test failures. Please check the API server.")
    
    return success_rate == 100

if __name__ == "__main__":
    main()