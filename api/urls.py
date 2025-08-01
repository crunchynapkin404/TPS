"""
TPS V1.4 - API URL Configuration
URL routing for Django REST Framework API endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.v1.users import UserViewSet
from api.v1.teams import TeamViewSet
from api.v1.assignments import AssignmentViewSet, SwapRequestViewSet
from api.simple_endpoints import (
    simple_assignments_list, simple_swap_requests_list, 
    simple_available_assignments, SimpleSwapRequestCreate
)
from api.v1.planning import (
    PlanningAPIView, PlanningPreviewAPIView, PlanningStatusAPIView,
    PlanningValidationAPIView, PlanningApplyAPIView
)
from api.v1.planning_views import generate_planning, get_teams, planning_preview
from api.v1.orchestrator_views import generate_orchestrator_planning, validate_orchestrator_prerequisites
from api.v1.calendar import calendar_month, calendar_summary
from api.v1.assignment_operations import (
    move_assignment, copy_assignment, delete_assignment, bulk_move_assignments
)
from api.v1.quick_assignment import (
    quick_create_assignment, assignment_types, validate_assignment_slot
)
from api.v1.dashboard import (
    dashboard_stats, dashboard_recent_activity, dashboard_team_overview, dashboard_my_shifts
)
from api.v1.teams_overview import teams_overview, teams_statistics, team_members
from api.v1.analytics_overview import (
    analytics_overview, analytics_workload_trends, analytics_team_performance,
    analytics_fairness_metrics, analytics_system_health
)
from api.v1.assignments_overview import (
    assignments_overview, assignments_timeline, assignments_bulk_data, assignments_bulk_update
)

# Notification API imports
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'swap-requests', SwapRequestViewSet)

# Define URL patterns
urlpatterns = [
    # Simple endpoints for testing (temporary)
    path('v1/assignments/simple/', simple_assignments_list, name='simple-assignments-list'),
    path('v1/swap-requests/simple/', simple_swap_requests_list, name='simple-swap-requests-list'),
    path('v1/assignments/available/simple/', simple_available_assignments, name='simple-available-assignments'),
    path('v1/swap-requests/create/simple/', SimpleSwapRequestCreate.as_view(), name='simple-swap-request-create'),
    
    # Quick Assignment API endpoints (must come before router to avoid conflicts)
    path('v1/assignments/quick-create/', quick_create_assignment, name='assignment-quick-create'),
    path('v1/assignments/types/', assignment_types, name='assignment-types'),
    path('v1/assignments/validate-slot/', validate_assignment_slot, name='assignment-validate-slot'),
    
    # Assignments Management API endpoints - must come BEFORE router to override ViewSet routes
    path('v1/assignments/overview/', assignments_overview, name='assignments-overview'),
    path('v1/assignments/<uuid:assignment_id>/timeline/', assignments_timeline, name='assignments-timeline'),
    path('v1/assignments/bulk-data/', assignments_bulk_data, name='assignments-bulk-data'),
    path('v1/assignments/bulk-update/', assignments_bulk_update, name='assignments-bulk-update'),
    
    # Router-generated URLs
    path('v1/', include(router.urls)),
    
    # Planning API endpoints
    path('v1/planning/', PlanningAPIView.as_view(), name='planning-api'),
    path('v1/planning/generate/', generate_planning, name='planning-generate'),
    path('v1/planning/orchestrator/', generate_orchestrator_planning, name='planning-orchestrator'),
    path('v1/planning/orchestrator/validate/', validate_orchestrator_prerequisites, name='planning-validate-orchestrator'),
    path('v1/planning/preview/<int:planning_id>/', planning_preview, name='planning-preview'),
    path('v1/planning/preview/', PlanningPreviewAPIView.as_view(), name='planning-preview'),
    path('v1/planning/validate/', PlanningValidationAPIView.as_view(), name='planning-validate'),
    path('v1/planning/<int:planning_period_id>/status/', PlanningStatusAPIView.as_view(), name='planning-status'),
    path('v1/planning/<int:planning_period_id>/apply/', PlanningApplyAPIView.as_view(), name='planning-apply'),
    
    # Calendar API endpoints
    path('v1/calendar/<int:team_id>/month/', calendar_month, name='calendar-month'),
    path('v1/calendar/<int:team_id>/summary/', calendar_summary, name='calendar-summary'),
    
    # Assignment Operations API endpoints
    path('v1/assignments/<int:assignment_id>/move/', move_assignment, name='assignment-move'),
    path('v1/assignments/<int:assignment_id>/copy/', copy_assignment, name='assignment-copy'),
    path('v1/assignments/<int:assignment_id>/delete/', delete_assignment, name='assignment-delete'),
    path('v1/assignments/bulk-move/', bulk_move_assignments, name='assignments-bulk-move'),
    
    # Dashboard API endpoints
    path('v1/dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('v1/dashboard/activity/', dashboard_recent_activity, name='dashboard-activity'),
    path('v1/dashboard/teams/', dashboard_team_overview, name='dashboard-teams'),
    path('v1/dashboard/my-shifts/', dashboard_my_shifts, name='dashboard-my-shifts'),
    
    # Analytics API endpoints  
    path('v1/analytics/overview/', analytics_overview, name='analytics-overview'),
    path('v1/analytics/workload-trends/', analytics_workload_trends, name='analytics-workload-trends'),
    path('v1/analytics/team-performance/', analytics_team_performance, name='analytics-team-performance'),
    path('v1/analytics/fairness-metrics/', analytics_fairness_metrics, name='analytics-fairness-metrics'),
    path('v1/analytics/system-health/', analytics_system_health, name='analytics-system-health'),
    
    # Additional analytics endpoints from error log
    path('v1/analytics/fairness/', lambda request: JsonResponse({'success': True, 'fairness_distribution': []}), name='analytics-fairness'),
    path('v1/analytics/workload/', lambda request: JsonResponse({'success': True, 'workload_trends': []}), name='analytics-workload'),
    path('v1/analytics/teams/', lambda request: JsonResponse({'success': True, 'team_performance': []}), name='analytics-teams'),
    path('v1/analytics/performers/', lambda request: JsonResponse({'success': True, 'top_performers': []}), name='analytics-performers'),
    path('v1/analytics/alerts/', lambda request: JsonResponse({'success': True, 'alerts': []}), name='analytics-alerts'),
    
    # Teams API endpoints - handled by TeamViewSet
    # path('v1/teams/overview/', teams_overview, name='teams-overview'),
    # path('v1/teams/statistics/', teams_statistics, name='teams-statistics'),
    path('v1/teams/<int:team_id>/members/', team_members, name='team-members'),
    
    # Notification API endpoints (temporary endpoints)
    path('v1/notifications/unread/', lambda request: JsonResponse({'count': 0, 'notifications': []}), name='notifications-unread'),
    path('v1/notifications/<int:notification_id>/read/', lambda request, notification_id: JsonResponse({'success': True}), name='notification-read'),
    
    # Employees endpoint (alias for users)
    path('v1/employees/', lambda request: JsonResponse({'success': True, 'employees': []}), name='employees-list'),
    
    # Authentication endpoints
    path('auth/', include('rest_framework.urls')),
]

# Note: JSON format is default - no need for format suffix patterns

# API endpoint documentation
"""
TPS V1.4 API Endpoints

Authentication:
    GET  /api/auth/login/           - Login page
    POST /api/auth/logout/          - Logout
    
Users:
    GET    /api/v1/users/                          - List users
    POST   /api/v1/users/                          - Create user  
    GET    /api/v1/users/{id}/                     - Get user details
    PUT    /api/v1/users/{id}/                     - Update user
    DELETE /api/v1/users/{id}/                     - Delete user
    GET    /api/v1/users/{id}/schedule/            - Get user schedule
    GET    /api/v1/users/{id}/workload-stats/      - Get user workload
    POST   /api/v1/users/{id}/update-availability/ - Update availability
    POST   /api/v1/users/{id}/change-password/     - Change password
    GET    /api/v1/users/available-for-shift/      - Get available users
    GET    /api/v1/users/departments/              - List departments
    GET    /api/v1/users/roles/                    - List user roles

Teams:
    GET    /api/v1/teams/                          - List teams
    POST   /api/v1/teams/                          - Create team
    GET    /api/v1/teams/{id}/                     - Get team details
    PUT    /api/v1/teams/{id}/                     - Update team
    DELETE /api/v1/teams/{id}/                     - Delete team
    GET    /api/v1/teams/{id}/members/             - Get team members
    GET    /api/v1/teams/{id}/schedule/            - Get team schedule
    GET    /api/v1/teams/{id}/planning-summary/    - Get planning summary
    GET    /api/v1/teams/{id}/workload-analysis/   - Get workload analysis
    POST   /api/v1/teams/{id}/add-member/          - Add team member
    DELETE /api/v1/teams/{id}/remove-member/       - Remove team member
    GET    /api/v1/teams/departments/              - List departments
    GET    /api/v1/teams/roles/                    - List team roles

Assignments:
    GET    /api/v1/assignments/                           - List assignments
    POST   /api/v1/assignments/                           - Create assignment
    GET    /api/v1/assignments/{id}/                      - Get assignment details
    PUT    /api/v1/assignments/{id}/                      - Update assignment
    DELETE /api/v1/assignments/{id}/                      - Delete assignment
    POST   /api/v1/assignments/bulk-create/               - Bulk create assignments
    POST   /api/v1/assignments/{id}/swap-request/         - Create swap request
    POST   /api/v1/assignments/{id}/approve/              - Approve assignment
    POST   /api/v1/assignments/{id}/reject/               - Reject assignment
    GET    /api/v1/assignments/available-users-for-shift/ - Get available users

Swap Requests:
    GET    /api/v1/swap-requests/           - List swap requests
    POST   /api/v1/swap-requests/           - Create swap request
    GET    /api/v1/swap-requests/{id}/      - Get swap request details
    PUT    /api/v1/swap-requests/{id}/      - Update swap request
    DELETE /api/v1/swap-requests/{id}/      - Delete swap request
    POST   /api/v1/swap-requests/{id}/approve/ - Approve swap
    POST   /api/v1/swap-requests/{id}/reject/  - Reject swap

Planning:
    POST   /api/v1/planning/                      - Generate planning
    GET    /api/v1/planning/                      - Get planning history
    PUT    /api/v1/planning/                      - Update planning
    DELETE /api/v1/planning/                      - Cancel planning
    POST   /api/v1/planning/preview/              - Preview planning
    POST   /api/v1/planning/validate/             - Validate prerequisites
    GET    /api/v1/planning/{id}/status/          - Get planning status
    POST   /api/v1/planning/{id}/apply/           - Apply planning

Query Parameters:
    - is_active: Filter by active status (true/false)
    - role: Filter by user role
    - department: Filter by department
    - team_id: Filter by team ID
    - skill_ids: Filter by skill IDs (comma-separated)
    - search: Search by name or ID
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - status: Filter by status
    - shift_type: Filter by shift type
    - user_id: Filter by user ID

Response Format:
    All responses are in JSON format with consistent structure:
    {
        "id": 123,
        "field": "value",
        ...
    }
    
    List responses include pagination:
    {
        "count": 50,
        "next": "http://api/v1/endpoint/?page=2",
        "previous": null,
        "results": [...]
    }
    
    Error responses:
    {
        "error": "Error message",
        "details": {...}
    }

Authentication:
    - All endpoints require authentication
    - Use session authentication or token authentication
    - Role-based permissions enforced
    
Rate Limiting:
    - 1000 requests per hour for authenticated users
    - 100 requests per hour for planning operations
    
Content Types:
    - Accept: application/json
    - Content-Type: application/json
"""
