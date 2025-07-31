"""
TPS V1.4 - WebSocket Routing
ASGI routing configuration for WebSocket consumers
"""

from django.urls import path
from api.consumers import NotificationConsumer, PlanningConsumer, AssignmentConsumer

websocket_urlpatterns = [
    # User notifications WebSocket
    path('ws/notifications/<int:user_id>/', NotificationConsumer.as_asgi()),
    
    # Planning progress WebSocket  
    path('ws/planning/<int:team_id>/', PlanningConsumer.as_asgi()),
    
    # Assignment updates WebSocket
    path('ws/assignments/', AssignmentConsumer.as_asgi()),
    
    # System status WebSocket
    path('ws/system/', AssignmentConsumer.as_asgi()),
]
