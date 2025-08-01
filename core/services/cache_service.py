"""
TPS V1.4 - Cache Service Layer
Centralized caching for performance optimization
"""

from typing import Dict, Any, Optional, List
from django.core.cache import cache
from django.conf import settings
from django.db.models import Model
from django.contrib.auth import get_user_model
import hashlib

User = get_user_model()


class CacheService:
    """
    Centralized caching service with intelligent cache keys and invalidation
    """
    
    # Cache timeouts (in seconds)
    USER_PERMISSIONS_TIMEOUT = 300      # 5 minutes
    DASHBOARD_DATA_TIMEOUT = 180        # 3 minutes
    TEAM_MEMBERSHIPS_TIMEOUT = 600      # 10 minutes
    SYSTEM_STATS_TIMEOUT = 120          # 2 minutes
    
    @classmethod
    def _make_cache_key(cls, *parts) -> str:
        """Create a consistent cache key from parts"""
        key_string = ':'.join(str(part) for part in parts)
        # Hash long keys to avoid cache key length limits
        if len(key_string) > 100:
            return f"tps:{hashlib.md5(key_string.encode()).hexdigest()}"
        return f"tps:{key_string}"
    
    @classmethod
    def get_user_permissions(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user permissions"""
        cache_key = cls._make_cache_key('user_permissions', user_id)
        return cache.get(cache_key)
    
    @classmethod
    def set_user_permissions(cls, user_id: int, permissions: Dict[str, Any]) -> None:
        """Cache user permissions"""
        cache_key = cls._make_cache_key('user_permissions', user_id)
        cache.set(cache_key, permissions, cls.USER_PERMISSIONS_TIMEOUT)
    
    @classmethod
    def invalidate_user_permissions(cls, user_id: int) -> None:
        """Invalidate cached user permissions"""
        cache_key = cls._make_cache_key('user_permissions', user_id)
        cache.delete(cache_key)
    
    @classmethod
    def get_user_teams(cls, user_id: int) -> Optional[List]:
        """Get cached user team memberships"""
        cache_key = cls._make_cache_key('user_teams', user_id)
        return cache.get(cache_key)
    
    @classmethod
    def set_user_teams(cls, user_id: int, teams: List) -> None:
        """Cache user team memberships"""
        cache_key = cls._make_cache_key('user_teams', user_id)
        cache.set(cache_key, teams, cls.TEAM_MEMBERSHIPS_TIMEOUT)
    
    @classmethod
    def invalidate_user_teams(cls, user_id: int) -> None:
        """Invalidate cached user team memberships"""
        cache_key = cls._make_cache_key('user_teams', user_id)
        cache.delete(cache_key)
    
    @classmethod
    def get_dashboard_data(cls, user_id: int, dashboard_type: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard data"""
        cache_key = cls._make_cache_key('dashboard', user_id, dashboard_type)
        return cache.get(cache_key)
    
    @classmethod
    def set_dashboard_data(cls, user_id: int, dashboard_type: str, data: Dict[str, Any]) -> None:
        """Cache dashboard data"""
        cache_key = cls._make_cache_key('dashboard', user_id, dashboard_type)
        cache.set(cache_key, data, cls.DASHBOARD_DATA_TIMEOUT)
    
    @classmethod
    def invalidate_dashboard_data(cls, user_id: int = None, dashboard_type: str = None) -> None:
        """Invalidate dashboard cache (specific user or all)"""
        if user_id and dashboard_type:
            cache_key = cls._make_cache_key('dashboard', user_id, dashboard_type)
            cache.delete(cache_key)
        else:
            # Clear all dashboard cache - use pattern if available
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern('tps:dashboard:*')
            else:
                # Fallback: clear entire cache (not ideal but works)
                cache.clear()
    
    @classmethod
    def get_system_stats(cls) -> Optional[Dict[str, Any]]:
        """Get cached system-wide statistics"""
        cache_key = cls._make_cache_key('system_stats')
        return cache.get(cache_key)
    
    @classmethod
    def set_system_stats(cls, stats: Dict[str, Any]) -> None:
        """Cache system-wide statistics"""
        cache_key = cls._make_cache_key('system_stats')
        cache.set(cache_key, stats, cls.SYSTEM_STATS_TIMEOUT)
    
    @classmethod
    def invalidate_system_stats(cls) -> None:
        """Invalidate system statistics cache"""
        cache_key = cls._make_cache_key('system_stats')
        cache.delete(cache_key)
    
    @classmethod
    def invalidate_all_user_cache(cls, user_id: int) -> None:
        """Invalidate all cache related to a specific user"""
        cls.invalidate_user_permissions(user_id)
        cls.invalidate_user_teams(user_id)
        cls.invalidate_dashboard_data(user_id)
    
    @classmethod
    def warm_user_cache(cls, user: User) -> None:
        """Pre-warm cache with user data"""
        from .user_service import UserService
        from apps.teams.models import Team
        
        # Cache user permissions
        permissions = {
            'role': user.role,
            'is_planner': user.is_planner(),
            'is_manager': user.is_manager(),
            'is_admin': user.is_admin(),
            'can_access_planning': user.can_access_planning(),
            'can_access_analytics': user.can_access_analytics(),
            'can_manage_teams': user.can_manage_teams(),
        }
        cls.set_user_permissions(user.id, permissions)
        
        # Cache user teams
        user_teams = list(Team.objects.filter(
            memberships__user=user,
            memberships__is_active=True
        ).distinct())
        cls.set_user_teams(user.id, user_teams)


class CacheInvalidationService:
    """
    Service for cache invalidation when models change
    """
    
    @classmethod
    def on_user_updated(cls, user_id: int) -> None:
        """Handle cache invalidation when user data changes"""
        CacheService.invalidate_all_user_cache(user_id)
        CacheService.invalidate_system_stats()
    
    @classmethod
    def on_team_membership_changed(cls, user_id: int) -> None:
        """Handle cache invalidation when team memberships change"""
        CacheService.invalidate_user_teams(user_id)
        CacheService.invalidate_dashboard_data(user_id)
    
    @classmethod
    def on_assignment_created_or_updated(cls) -> None:
        """Handle cache invalidation when assignments change"""
        CacheService.invalidate_system_stats()
        # Invalidate all dashboard data as assignments affect multiple views
        CacheService.invalidate_dashboard_data()
    
    @classmethod
    def on_leave_request_changed(cls) -> None:
        """Handle cache invalidation when leave requests change"""
        CacheService.invalidate_system_stats()
        # Leave requests affect manager and admin dashboards
        CacheService.invalidate_dashboard_data()