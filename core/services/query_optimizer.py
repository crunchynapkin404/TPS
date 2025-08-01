"""
TPS Query Optimization Service
Identifies and resolves N+1 query problems and other performance issues
"""
from django.db import connection
from django.db.models import Prefetch, Q
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from typing import List, Dict, Any, Optional
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger('tps.query_optimization')


class QueryOptimizer:
    """Service class for identifying and optimizing database queries"""
    
    def __init__(self):
        self.query_log = []
        self.slow_query_threshold = 100  # milliseconds
    
    @contextmanager
    def query_monitor(self, operation_name: str):
        """Context manager to monitor query performance"""
        initial_queries = len(connection.queries)
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            new_queries = len(connection.queries) - initial_queries
            duration_ms = (end_time - start_time) * 1000
            
            self.query_log.append({
                'operation': operation_name,
                'query_count': new_queries,
                'duration_ms': duration_ms,
                'is_slow': duration_ms > self.slow_query_threshold
            })
            
            if duration_ms > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected: {operation_name} took {duration_ms:.2f}ms with {new_queries} queries"
                )
    
    def get_optimized_user_queryset(self):
        """Optimized queryset for User objects with related data"""
        from apps.accounts.models import User
        
        return User.objects.select_related(
            # No immediate foreign keys to select_related on User model
        ).prefetch_related(
            'team_memberships__team',
            'team_memberships__role',
            'user_skills__skill__category',
            'shift_assignments__shift__template__category',
            Prefetch(
                'user_skills',
                queryset=User.objects.get_model().user_skills.through.objects.select_related(
                    'skill__category'
                ).filter(is_certified=True)
            )
        )
    
    def get_optimized_assignment_queryset(self):
        """Optimized queryset for Assignment objects"""
        from apps.assignments.models import Assignment
        
        return Assignment.objects.select_related(
            'user',
            'shift__template__category',
            'assigned_by',
        ).prefetch_related(
            'history__actor',
            'user__team_memberships__team',
            'user__user_skills__skill'
        )
    
    def get_optimized_shift_queryset(self):
        """Optimized queryset for ShiftInstance objects"""
        from apps.scheduling.models import ShiftInstance
        
        return ShiftInstance.objects.select_related(
            'template__category',
            'planning_period',
            'created_by'
        ).prefetch_related(
            'assignments__user',
            'assignments__user__team_memberships__team',
            Prefetch(
                'assignments',
                queryset=Assignment.objects.select_related('user').filter(
                    assignment_type='primary'
                )
            )
        )
    
    def get_optimized_team_queryset(self):
        """Optimized queryset for Team objects"""
        from apps.teams.models import Team
        
        return Team.objects.select_related(
            'team_leader'
        ).prefetch_related(
            'memberships__user',
            'memberships__role',
            Prefetch(
                'memberships',
                queryset=Team.objects.get_model().memberships.through.objects.select_related(
                    'user', 'role'
                ).filter(is_active=True)
            )
        )
    
    def analyze_user_dashboard_queries(self, user_id: int) -> Dict[str, Any]:
        """Analyze queries for user dashboard and provide optimization suggestions"""
        from apps.accounts.models import User
        from apps.assignments.models import Assignment
        
        analysis = {
            'optimizations_applied': [],
            'query_counts': {},
            'suggestions': []
        }
        
        # Test current approach
        with self.query_monitor('user_dashboard_current'):
            user = User.objects.get(id=user_id)
            assignments = list(user.shift_assignments.all()[:10])
            teams = list(user.team_memberships.all())
            skills = list(user.user_skills.all())
        
        current_stats = self.query_log[-1]
        analysis['query_counts']['current'] = current_stats['query_count']
        
        # Test optimized approach
        with self.query_monitor('user_dashboard_optimized'):
            user = User.objects.select_related().prefetch_related(
                'shift_assignments__shift__template',
                'team_memberships__team',
                'team_memberships__role',
                'user_skills__skill__category'
            ).get(id=user_id)
            
            assignments = list(user.shift_assignments.all()[:10])
            teams = list(user.team_memberships.all())
            skills = list(user.user_skills.all())
        
        optimized_stats = self.query_log[-1]
        analysis['query_counts']['optimized'] = optimized_stats['query_count']
        
        # Calculate improvement
        query_reduction = current_stats['query_count'] - optimized_stats['query_count']
        time_reduction = current_stats['duration_ms'] - optimized_stats['duration_ms']
        
        analysis['optimizations_applied'] = [
            f"Reduced queries by {query_reduction}",
            f"Reduced time by {time_reduction:.2f}ms"
        ]
        
        # Provide suggestions
        if query_reduction > 0:
            analysis['suggestions'].append(
                "Use prefetch_related for related objects in user dashboard views"
            )
        
        return analysis
    
    def analyze_shift_planning_queries(self, date_range: tuple) -> Dict[str, Any]:
        """Analyze queries for shift planning page"""
        from apps.scheduling.models import ShiftInstance
        from apps.assignments.models import Assignment
        
        start_date, end_date = date_range
        analysis = {'optimizations_applied': [], 'suggestions': []}
        
        # Test current approach
        with self.query_monitor('shift_planning_current'):
            shifts = ShiftInstance.objects.filter(
                date__range=[start_date, end_date]
            )[:50]
            
            for shift in shifts:
                assignments = list(shift.assignments.all())
                for assignment in assignments:
                    user_name = assignment.user.get_full_name()
                    team_name = assignment.user.team_memberships.first().team.name
        
        current_stats = self.query_log[-1]
        
        # Test optimized approach
        with self.query_monitor('shift_planning_optimized'):
            shifts = ShiftInstance.objects.filter(
                date__range=[start_date, end_date]
            ).select_related(
                'template__category'
            ).prefetch_related(
                'assignments__user__team_memberships__team',
                'assignments__user__team_memberships__role'
            )[:50]
            
            for shift in shifts:
                assignments = list(shift.assignments.all())
                for assignment in assignments:
                    user_name = assignment.user.get_full_name()
                    team_name = assignment.user.team_memberships.first().team.name
        
        optimized_stats = self.query_log[-1]
        
        query_reduction = current_stats['query_count'] - optimized_stats['query_count']
        analysis['optimizations_applied'].append(f"Reduced queries by {query_reduction}")
        
        return analysis
    
    def get_cache_optimization_suggestions(self) -> List[str]:
        """Provide caching optimization suggestions"""
        suggestions = [
            "Cache user permissions and roles for 5-10 minutes",
            "Cache team membership data for active users",
            "Cache shift templates and categories (rarely change)",
            "Use database-level query result caching for complex aggregations",
            "Implement Redis caching for user dashboard data",
            "Cache skill category and skill data (static reference data)"
        ]
        return suggestions
    
    def generate_query_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive query optimization report"""
        report = {
            'timestamp': time.time(),
            'slow_queries': [q for q in self.query_log if q['is_slow']],
            'query_patterns': self._analyze_query_patterns(),
            'optimization_suggestions': self._get_optimization_suggestions(),
            'performance_metrics': self._calculate_performance_metrics()
        }
        return report
    
    def _analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze common query patterns in the log"""
        patterns = {
            'n_plus_one_detected': False,
            'repeated_queries': 0,
            'average_queries_per_operation': 0
        }
        
        if self.query_log:
            patterns['average_queries_per_operation'] = sum(
                q['query_count'] for q in self.query_log
            ) / len(self.query_log)
            
            # Simple N+1 detection (operations with >10 queries are suspicious)
            patterns['n_plus_one_detected'] = any(
                q['query_count'] > 10 for q in self.query_log
            )
        
        return patterns
    
    def _get_optimization_suggestions(self) -> List[str]:
        """Generate optimization suggestions based on analysis"""
        suggestions = [
            "Use select_related() for foreign key relationships",
            "Use prefetch_related() for reverse foreign keys and many-to-many",
            "Implement database query result caching",
            "Add database indexes for frequently queried fields",
            "Use bulk operations for multiple database writes",
            "Consider denormalizing frequently accessed data"
        ]
        return suggestions
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from query log"""
        if not self.query_log:
            return {}
        
        durations = [q['duration_ms'] for q in self.query_log]
        query_counts = [q['query_count'] for q in self.query_log]
        
        return {
            'average_duration_ms': sum(durations) / len(durations),
            'max_duration_ms': max(durations),
            'average_query_count': sum(query_counts) / len(query_counts),
            'max_query_count': max(query_counts),
            'slow_query_percentage': len([q for q in self.query_log if q['is_slow']]) / len(self.query_log) * 100
        }


# Global instance for use across the application
query_optimizer = QueryOptimizer()


def optimize_user_related_queries(queryset):
    """Helper function to optimize user-related queries"""
    return queryset.select_related().prefetch_related(
        'team_memberships__team',
        'team_memberships__role',
        'user_skills__skill__category'
    )


def optimize_assignment_queries(queryset):
    """Helper function to optimize assignment queries"""
    return queryset.select_related(
        'user',
        'shift__template__category',
        'assigned_by'
    ).prefetch_related(
        'user__team_memberships__team'
    )


def optimize_shift_queries(queryset):
    """Helper function to optimize shift queries"""
    return queryset.select_related(
        'template__category',
        'planning_period'
    ).prefetch_related(
        'assignments__user__team_memberships__team'
    )