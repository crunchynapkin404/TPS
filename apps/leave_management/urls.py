"""
TPS V1.4 - Leave Management URLs
URL patterns for leave request system
"""

from django.urls import path
from . import views

app_name = 'leave_management'

urlpatterns = [
    # Overview and listing
    path('', views.LeaveOverviewView.as_view(), name='overview'),
    path('calendar/', views.LeaveCalendarView.as_view(), name='calendar'),
    
    # Leave request management
    path('request/new/', views.LeaveRequestCreateView.as_view(), name='create_request'),
    path('request/<int:pk>/', views.LeaveRequestDetailView.as_view(), name='detail'),
    path('request/<int:pk>/submit/', views.submit_leave_request, name='submit_request'),
    path('request/<int:pk>/cancel/', views.cancel_leave_request, name='cancel_request'),
    
    # Manager actions
    path('request/<int:pk>/approve/', views.approve_leave_request, name='approve_request'),
    path('request/<int:pk>/decline/', views.decline_leave_request, name='decline_request'),
    
    # API endpoints
    path('api/balance/', views.leave_balance_api, name='balance_api'),
]