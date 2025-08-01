"""
TPS V1.4 - Lazy Loading Service
Implements lazy loading patterns for heavy operations and data
"""

from typing import Dict, Any, List, Optional, Callable
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from functools import wraps, lru_cache
import time
import logging

from core.services.cache_service import CacheService

User = get_user_model()
logger = logging.getLogger(__name__)


class LazyLoadingService:
    """
    Service for implementing lazy loading patterns to improve performance
    """
    
    @classmethod
    def lazy_property(cls, func):
        """
        Decorator to create lazy properties that are computed only when accessed
        """
        attr_name = f'_lazy_{func.__name__}'
        
        @property
        @wraps(func)
        def wrapper(self):
            if not hasattr(self, attr_name):
                start_time = time.time()
                result = func(self)
                end_time = time.time()
                
                setattr(self, attr_name, result)
                logger.debug(f"Lazy loaded {func.__name__} in {end_time - start_time:.4f}s")
            
            return getattr(self, attr_name)
        
        return wrapper
    
    @classmethod
    def lazy_queryset(cls, timeout: int = 300):
        """
        Decorator to cache expensive querysets with lazy evaluation
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                cache_key = f"lazy_queryset_{func.__name__}_{hash(str(args) + str(kwargs))}"
                
                # Try to get from cache first
                cached_result = CacheService.get_dashboard_data(
                    args[0].id if hasattr(args[0], 'id') else 0,
                    cache_key
                )
                
                if cached_result is not None:
                    logger.debug(f"Cache hit for lazy queryset {func.__name__}")
                    return cached_result
                
                # Execute query and cache result
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Convert QuerySet to list for caching
                if isinstance(result, QuerySet):
                    result_list = list(result)
                else:
                    result_list = result
                
                CacheService.set_dashboard_data(
                    args[0].id if hasattr(args[0], 'id') else 0,
                    cache_key,
                    result_list
                )
                
                logger.debug(f"Lazy loaded and cached queryset {func.__name__} in {end_time - start_time:.4f}s")
                return result_list
            
            return wrapper
        return decorator
    
    @classmethod
    def paginated_lazy_loader(cls, page_size: int = 20):
        """
        Create a paginated lazy loader for large datasets
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self, page: int = 1, **kwargs):
                cache_key = f"paginated_{func.__name__}_page_{page}_{hash(str(kwargs))}"
                
                # Try cache first
                cached_page = CacheService.get_dashboard_data(
                    getattr(self, 'id', 0),
                    cache_key
                )
                
                if cached_page is not None:
                    return cached_page
                
                # Calculate offset
                offset = (page - 1) * page_size
                
                # Get paginated results
                all_results = func(self, **kwargs)
                
                if isinstance(all_results, QuerySet):
                    paginated_results = all_results[offset:offset + page_size]
                    total_count = all_results.count()
                else:
                    paginated_results = all_results[offset:offset + page_size]
                    total_count = len(all_results)
                
                page_data = {
                    'results': list(paginated_results),
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'has_next': offset + page_size < total_count,
                    'has_previous': page > 1,
                }
                
                # Cache the page
                CacheService.set_dashboard_data(
                    getattr(self, 'id', 0),
                    cache_key,
                    page_data
                )
                
                return page_data
            
            return wrapper
        return decorator


class LazyDataLoader:
    """
    Context manager for lazy loading of related data
    """
    
    def __init__(self, user: User):
        self.user = user
        self._loaded_data = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Optional: Clear temporary data
        self._loaded_data.clear()
    
    def get_user_teams(self) -> List:
        """Lazy load user teams"""
        if 'user_teams' not in self._loaded_data:
            from core.services.query_optimization_service import QueryOptimizationService
            self._loaded_data['user_teams'] = QueryOptimizationService.get_user_teams_optimized(self.user.id)
        return self._loaded_data['user_teams']
    
    def get_user_assignments(self, limit: int = None) -> List:
        """Lazy load user assignments"""
        cache_key = f'user_assignments_{limit or "all"}'
        
        if cache_key not in self._loaded_data:
            from apps.assignments.models import Assignment
            
            queryset = Assignment.objects.filter(
                user=self.user
            ).select_related(
                'shift__template',
                'shift__planning_period'
            ).prefetch_related(
                'shift__planning_period__teams'
            ).order_by('-assigned_at')
            
            if limit:
                queryset = queryset[:limit]
            
            self._loaded_data[cache_key] = list(queryset)
        
        return self._loaded_data[cache_key]
    
    def get_workload_stats(self, days: int = 30) -> Dict[str, Any]:
        """Lazy load workload statistics"""
        cache_key = f'workload_stats_{days}'
        
        if cache_key not in self._loaded_data:
            from core.services.query_optimization_service import QueryOptimizationService
            self._loaded_data[cache_key] = QueryOptimizationService.get_user_workload_analysis(
                self.user.id, days
            )
        
        return self._loaded_data[cache_key]


class DeferredCalculation:
    """
    Wrapper for expensive calculations that should be deferred until needed
    """
    
    def __init__(self, calculation_func: Callable, *args, **kwargs):
        self.calculation_func = calculation_func
        self.args = args
        self.kwargs = kwargs
        self._result = None
        self._calculated = False
    
    def __call__(self):
        if not self._calculated:
            start_time = time.time()
            self._result = self.calculation_func(*self.args, **self.kwargs)
            end_time = time.time()
            self._calculated = True
            
            logger.debug(f"Deferred calculation completed in {end_time - start_time:.4f}s")
        
        return self._result
    
    @property
    def is_calculated(self) -> bool:
        return self._calculated
    
    def reset(self):
        """Reset the calculation to allow recalculation"""
        self._calculated = False
        self._result = None


class StreamingDataProvider:
    """
    Provider for streaming large datasets to avoid memory issues
    """
    
    def __init__(self, queryset: QuerySet, chunk_size: int = 100):
        self.queryset = queryset
        self.chunk_size = chunk_size
    
    def __iter__(self):
        """Iterator that yields chunks of data"""
        offset = 0
        
        while True:
            chunk = list(self.queryset[offset:offset + self.chunk_size])
            if not chunk:
                break
            
            yield chunk
            offset += self.chunk_size
    
    def stream_json(self, serializer_func: Callable = None):
        """Stream data as JSON objects"""
        for chunk in self:
            if serializer_func:
                yield [serializer_func(item) for item in chunk]
            else:
                yield [item.to_dict() if hasattr(item, 'to_dict') else str(item) for item in chunk]


# Enhanced model mixins for lazy loading
class LazyLoadMixin:
    """
    Mixin to add lazy loading capabilities to Django models
    """
    
    @LazyLoadingService.lazy_property
    def lazy_related_count(self):
        """Example lazy property for counting related objects"""
        return self.related_objects.count()
    
    def get_paginated_related(self, page: int = 1, page_size: int = 20):
        """Get paginated related objects"""
        @LazyLoadingService.paginated_lazy_loader(page_size)
        def _get_related(self, **kwargs):
            return self.related_objects.all()
        
        return _get_related(self, page=page)
    
    def stream_related_data(self, chunk_size: int = 100):
        """Stream related data in chunks"""
        return StreamingDataProvider(self.related_objects.all(), chunk_size)


# Context processor for lazy loading in templates
def lazy_loading_context_processor(request):
    """
    Context processor that provides lazy loading utilities in templates
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}
    
    return {
        'lazy_loader': LazyDataLoader(request.user),
        'deferred_calculations': {},  # Can be populated by views
    }


# Utility functions for common lazy loading patterns
def lazy_load_user_dashboard_data(user: User) -> Dict[str, Any]:
    """
    Lazy load complete user dashboard data with deferred calculations
    """
    dashboard_data = {}
    
    # Immediate data (small/fast queries)
    dashboard_data['user_info'] = {
        'id': user.id,
        'name': user.get_full_name(),
        'role': user.role,
    }
    
    # Deferred calculations (expensive operations)
    dashboard_data['assignments_count'] = DeferredCalculation(
        lambda: user.shift_assignments.count()
    )
    
    dashboard_data['workload_analysis'] = DeferredCalculation(
        lambda: QueryOptimizationService.get_user_workload_analysis(user.id)
    )
    
    dashboard_data['team_stats'] = DeferredCalculation(
        lambda: [
            QueryOptimizationService.get_team_workload_stats([team.id])
            for team in QueryOptimizationService.get_user_teams_optimized(user.id)
        ]
    )
    
    return dashboard_data


def create_lazy_model_property(field_name: str, related_manager: str):
    """
    Factory function to create lazy properties for model fields
    """
    def lazy_property(self):
        cache_key = f'lazy_{field_name}_{self.pk}'
        cached_value = getattr(self, f'_cached_{field_name}', None)
        
        if cached_value is None:
            manager = getattr(self, related_manager)
            cached_value = manager.count()  # or other expensive operation
            setattr(self, f'_cached_{field_name}', cached_value)
        
        return cached_value
    
    return property(lazy_property)