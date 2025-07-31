"""
TPS V1.4 - API Permissions
Enhanced permission classes for role-based access control
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from django.contrib.auth import get_user_model

User = get_user_model()


class TPSPermission(BasePermission):
    """Base permission class for TPS system with role-based access control"""
    
    def has_permission(self, request, view):
        """Check if user has permission to access the view"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Always allow authenticated users basic access
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers all access
        if request.user.is_superuser:
            return True
        
        # Object-specific permissions will be implemented in subclasses
        return True


class RoleBasedPermission(BasePermission):
    """Role-based permission checking for TPS user roles"""
    
    # Role hierarchy from V1.3.1 analysis
    ROLE_HIERARCHY = {
        'operationeel': 1,   # Basic engineers
        'tactisch': 2,       # Team leads and coordinators  
        'management': 3,     # Department managers
        'planner': 4,        # Dedicated planning staff
        'admin': 5           # System administrators
    }
    
    def __init__(self, required_role='operationeel'):
        self.required_role = required_role
    
    def has_permission(self, request, view):
        """Check if user has required role level"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers all access
        if request.user.is_superuser:
            return True
        
        # Get user role level
        user_role = getattr(request.user, 'role', 'operationeel')
        user_level = self.ROLE_HIERARCHY.get(user_role, 0)
        required_level = self.ROLE_HIERARCHY.get(self.required_role, 1)
        
        return user_level >= required_level
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions based on role"""
        return self.has_permission(request, view)


class OperationalPermission(RoleBasedPermission):
    """Permission for operational level users and above"""
    def __init__(self):
        super().__init__(required_role='operationeel')


class TacticalPermission(RoleBasedPermission):
    """Permission for tactical level users and above"""
    def __init__(self):
        super().__init__(required_role='tactisch')


class ManagementPermission(RoleBasedPermission):
    """Permission for management level users and above"""
    def __init__(self):
        super().__init__(required_role='management')


class PlannerPermission(RoleBasedPermission):
    """Permission for planner level users and above"""
    def __init__(self):
        super().__init__(required_role='planner')


class AdminPermission(RoleBasedPermission):
    """Permission for admin level users only"""
    def __init__(self):
        super().__init__(required_role='admin')


class TeamMemberPermission(BasePermission):
    """Permission for team members to access team-related data"""
    
    def has_permission(self, request, view):
        """Basic authentication check"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user is member of the team or has higher permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers and management+ roles
        if request.user.is_superuser:
            return True
        
        user_role = getattr(request.user, 'role', 'operationeel')
        if RoleBasedPermission.ROLE_HIERARCHY.get(user_role, 0) >= 3:  # management+
            return True
        
        # Check if user is member of the team
        if hasattr(obj, 'teams'):
            # For user objects, check their team memberships
            return obj.teams.filter(
                teammembership__user=request.user,
                teammembership__is_active=True
            ).exists()
        elif hasattr(obj, 'team'):
            # For objects with team relationship
            return obj.team.memberships.filter(
                user=request.user,
                is_active=True
            ).exists()
        
        return False


class SelfOrManagerPermission(BasePermission):
    """Permission allowing users to access their own data or managers to access subordinate data"""
    
    def has_permission(self, request, view):
        """Basic authentication check"""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access the object (self or managed user)"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Allow tactical+ roles to access team member data
        user_role = getattr(request.user, 'role', 'operationeel')
        if RoleBasedPermission.ROLE_HIERARCHY.get(user_role, 0) >= 2:  # tactical+
            # Check if target user is in a team managed by current user
            if hasattr(obj, 'teams'):
                managed_teams = request.user.managed_teams.all()
                return obj.teams.filter(id__in=managed_teams).exists()
        
        # Allow users to access their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False


class ReadOnlyOrManagerPermission(BasePermission):
    """Permission allowing read-only access to all, write access to managers"""
    
    def has_permission(self, request, view):
        """Allow read access to authenticated users, write access to managers"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read access to all authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Allow write access to tactical+ roles
        user_role = getattr(request.user, 'role', 'operationeel')
        return RoleBasedPermission.ROLE_HIERARCHY.get(user_role, 0) >= 2  # tactical+


class PlanningPermission(BasePermission):
    """Special permission for planning operations"""
    
    def has_permission(self, request, view):
        """Allow planning operations only to planner+ roles"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Allow planner+ roles
        user_role = getattr(request.user, 'role', 'operationeel')
        return RoleBasedPermission.ROLE_HIERARCHY.get(user_role, 0) >= 4  # planner+
