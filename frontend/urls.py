from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Core Pages (Ready for Enhanced Templates)
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('teams/', views.TeamsView.as_view(), name='teams'),
    path('teams/<int:team_id>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('schedule/', views.ScheduleView.as_view(), name='schedule'),
    path('schedule/new/', views.ScheduleNewView.as_view(), name='schedule_new'),
    path('calendar/', views.CalendarUnifiedView.as_view(), name='calendar_unified'),
    path('assignments/', views.AssignmentsView.as_view(), name='assignments'),
    path('planning/', views.PlanningView.as_view(), name='planning'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # TODO: Additional Enhanced URLs to be added later
    # These will be implemented as we create the corresponding views:
    # - Planning wizard (/planning/wizard/)
    # - Quick actions API endpoints
    # - Analytics sub-pages (fairness, workload, coverage)
    # - Team management features
    # - Assignment CRUD operations
    # - Notification system
    # - User preferences and availability
]
