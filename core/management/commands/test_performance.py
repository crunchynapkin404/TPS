"""
Django management command to test performance optimizations
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from django.contrib.auth import get_user_model
import time
from typing import Dict, Any

from core.services.dashboard_service import DashboardService
from core.services.query_optimization_service import QueryOptimizationService
from core.services.cache_service import CacheService
from apps.teams.models import Team

User = get_user_model()


class Command(BaseCommand):
    help = 'Test performance optimizations and generate benchmarks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=10,
            help='Number of iterations for each test'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear cache before running tests'
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting performance tests with {iterations} iterations...')
        )
        
        if options['clear_cache']:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write('Cache cleared.')
        
        # Get test users
        test_users = self._get_test_users()
        
        if not test_users:
            self.stdout.write(
                self.style.ERROR('No test users found. Please create some users first.')
            )
            return
        
        # Run performance tests
        results = {}
        
        # Test dashboard loading
        results['dashboard_loading'] = self._test_dashboard_loading(test_users, iterations)
        
        # Test query optimization service
        results['query_optimization'] = self._test_query_optimization(test_users, iterations)
        
        # Test caching performance
        results['caching'] = self._test_caching_performance(test_users, iterations)
        
        # Test database query counts
        results['query_counts'] = self._test_query_counts(test_users)
        
        # Display results
        self._display_results(results)

    def _get_test_users(self):
        """Get test users for different roles"""
        test_users = {}
        
        # Get one user of each role type
        for role in ['USER', 'PLANNER', 'MANAGER', 'ADMIN']:
            user = User.objects.filter(role=role, is_active=True).first()
            if user:
                test_users[role] = user
        
        return test_users

    def _test_dashboard_loading(self, test_users: Dict[str, User], iterations: int) -> Dict[str, Any]:
        """Test dashboard loading performance"""
        self.stdout.write('Testing dashboard loading performance...')
        
        results = {}
        
        for role, user in test_users.items():
            times = []
            query_counts = []
            
            for _ in range(iterations):
                # Clear cache for this test
                CacheService.invalidate_all_user_cache(user.id)
                
                # Reset query count
                connection.queries_log.clear()
                
                start_time = time.time()
                dashboard_context = DashboardService.get_dashboard_context(user)
                end_time = time.time()
                
                times.append(end_time - start_time)
                query_counts.append(len(connection.queries))
            
            results[role] = {
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'avg_queries': sum(query_counts) / len(query_counts),
                'min_queries': min(query_counts),
                'max_queries': max(query_counts),
            }
        
        return results

    def _test_query_optimization(self, test_users: Dict[str, User], iterations: int) -> Dict[str, Any]:
        """Test query optimization service performance"""
        self.stdout.write('Testing query optimization service...')
        
        results = {}
        
        # Test system health metrics
        times = []
        query_counts = []
        
        for _ in range(iterations):
            CacheService.invalidate_system_stats()
            connection.queries_log.clear()
            
            start_time = time.time()
            metrics = QueryOptimizationService.get_system_health_metrics()
            end_time = time.time()
            
            times.append(end_time - start_time)
            query_counts.append(len(connection.queries))
        
        results['system_health_metrics'] = {
            'avg_time': sum(times) / len(times),
            'avg_queries': sum(query_counts) / len(query_counts),
        }
        
        # Test user dashboard data
        if 'USER' in test_users:
            user = test_users['USER']
            times = []
            query_counts = []
            
            for _ in range(iterations):
                CacheService.invalidate_all_user_cache(user.id)
                connection.queries_log.clear()
                
                start_time = time.time()
                data = QueryOptimizationService.get_user_dashboard_data(user)
                end_time = time.time()
                
                times.append(end_time - start_time)
                query_counts.append(len(connection.queries))
            
            results['user_dashboard_data'] = {
                'avg_time': sum(times) / len(times),
                'avg_queries': sum(query_counts) / len(query_counts),
            }
        
        return results

    def _test_caching_performance(self, test_users: Dict[str, User], iterations: int) -> Dict[str, Any]:
        """Test caching performance"""
        self.stdout.write('Testing caching performance...')
        
        results = {}
        
        if 'USER' in test_users:
            user = test_users['USER']
            
            # Test cache miss (first load)
            CacheService.invalidate_all_user_cache(user.id)
            start_time = time.time()
            dashboard_context = DashboardService.get_dashboard_context(user)
            cache_miss_time = time.time() - start_time
            
            # Test cache hit (subsequent loads)
            cache_hit_times = []
            for _ in range(iterations):
                start_time = time.time()
                dashboard_context = DashboardService.get_dashboard_context(user)
                cache_hit_times.append(time.time() - start_time)
            
            avg_cache_hit_time = sum(cache_hit_times) / len(cache_hit_times)
            
            results['cache_performance'] = {
                'cache_miss_time': cache_miss_time,
                'avg_cache_hit_time': avg_cache_hit_time,
                'speedup_ratio': cache_miss_time / avg_cache_hit_time if avg_cache_hit_time > 0 else 0,
            }
        
        return results

    def _test_query_counts(self, test_users: Dict[str, User]) -> Dict[str, Any]:
        """Test database query counts for various operations"""
        self.stdout.write('Testing database query counts...')
        
        results = {}
        
        for role, user in test_users.items():
            # Clear cache to ensure fresh queries
            CacheService.invalidate_all_user_cache(user.id)
            
            connection.queries_log.clear()
            dashboard_context = DashboardService.get_dashboard_context(user)
            query_count = len(connection.queries)
            
            results[f'{role}_dashboard_queries'] = query_count
        
        # Test team workload stats (potential N+1 issue)
        team_ids = list(Team.objects.values_list('id', flat=True)[:5])
        connection.queries_log.clear()
        workload_stats = QueryOptimizationService.get_team_workload_stats(team_ids)
        results['team_workload_queries'] = len(connection.queries)
        
        return results

    def _display_results(self, results: Dict[str, Any]):
        """Display performance test results"""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('PERFORMANCE TEST RESULTS'))
        self.stdout.write('='*80 + '\n')
        
        # Dashboard loading results
        if 'dashboard_loading' in results:
            self.stdout.write(self.style.WARNING('Dashboard Loading Performance:'))
            for role, stats in results['dashboard_loading'].items():
                self.stdout.write(f'  {role}:')
                self.stdout.write(f'    Average time: {stats["avg_time"]:.4f}s')
                self.stdout.write(f'    Average queries: {stats["avg_queries"]:.1f}')
                self.stdout.write(f'    Time range: {stats["min_time"]:.4f}s - {stats["max_time"]:.4f}s')
            self.stdout.write('')
        
        # Query optimization results
        if 'query_optimization' in results:
            self.stdout.write(self.style.WARNING('Query Optimization Service:'))
            for operation, stats in results['query_optimization'].items():
                self.stdout.write(f'  {operation}:')
                self.stdout.write(f'    Average time: {stats["avg_time"]:.4f}s')
                self.stdout.write(f'    Average queries: {stats["avg_queries"]:.1f}')
            self.stdout.write('')
        
        # Caching results
        if 'caching' in results and 'cache_performance' in results['caching']:
            cache_perf = results['caching']['cache_performance']
            self.stdout.write(self.style.WARNING('Caching Performance:'))
            self.stdout.write(f'  Cache miss time: {cache_perf["cache_miss_time"]:.4f}s')
            self.stdout.write(f'  Average cache hit time: {cache_perf["avg_cache_hit_time"]:.4f}s')
            self.stdout.write(f'  Speedup ratio: {cache_perf["speedup_ratio"]:.1f}x')
            self.stdout.write('')
        
        # Query count results
        if 'query_counts' in results:
            self.stdout.write(self.style.WARNING('Database Query Counts:'))
            for operation, count in results['query_counts'].items():
                self.stdout.write(f'  {operation}: {count} queries')
            self.stdout.write('')
        
        # Performance recommendations
        self._display_recommendations(results)

    def _display_recommendations(self, results: Dict[str, Any]):
        """Display performance recommendations based on test results"""
        self.stdout.write(self.style.WARNING('Performance Recommendations:'))
        
        recommendations = []
        
        # Check query counts
        if 'query_counts' in results:
            for operation, count in results['query_counts'].items():
                if count > 20:
                    recommendations.append(
                        f'  ⚠️  {operation} uses {count} queries - consider further optimization'
                    )
                elif count <= 5:
                    recommendations.append(
                        f'  ✅ {operation} uses only {count} queries - well optimized'
                    )
        
        # Check caching effectiveness
        if 'caching' in results and 'cache_performance' in results['caching']:
            speedup = results['caching']['cache_performance']['speedup_ratio']
            if speedup > 5:
                recommendations.append(
                    f'  ✅ Caching provides {speedup:.1f}x speedup - excellent performance gain'
                )
            elif speedup > 2:
                recommendations.append(
                    f'  ✅ Caching provides {speedup:.1f}x speedup - good performance gain'
                )
            else:
                recommendations.append(
                    f'  ⚠️  Caching provides only {speedup:.1f}x speedup - consider cache tuning'
                )
        
        if not recommendations:
            recommendations.append('  ✅ All performance metrics look good!')
        
        for rec in recommendations:
            self.stdout.write(rec)
        
        self.stdout.write('\n' + '='*80)