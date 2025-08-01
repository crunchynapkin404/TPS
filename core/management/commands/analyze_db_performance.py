"""
Database Analysis and Performance Testing Command
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth import get_user_model
from apps.teams.models import Team
from apps.assignments.models import Assignment
from core.services.query_optimizer import query_optimizer
import time

User = get_user_model()


class Command(BaseCommand):
    help = 'Analyze database performance and query patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-n-plus-one',
            action='store_true',
            help='Test for N+1 query problems',
        )
        parser.add_argument(
            '--analyze-indexes',
            action='store_true',
            help='Analyze index usage',
        )
        parser.add_argument(
            '--test-optimizations',
            action='store_true',
            help='Test query optimizations',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Database Performance Analysis'))
        
        if options['test_n_plus_one']:
            self._test_n_plus_one_queries()
        
        if options['analyze_indexes']:
            self._analyze_index_usage()
        
        if options['test_optimizations']:
            self._test_query_optimizations()
        
        # Always run general analysis
        self._run_general_analysis()

    def _test_n_plus_one_queries(self):
        """Test for N+1 query problems"""
        self.stdout.write('\n=== N+1 Query Testing ===')
        
        # Test 1: User team memberships (potential N+1)
        self.stdout.write('\nTesting User Team Memberships...')
        
        # Unoptimized - likely to cause N+1
        start_queries = len(connection.queries)
        users = User.objects.all()[:5]
        for user in users:
            memberships = list(user.team_memberships.all())
            for membership in memberships:
                team_name = membership.team.name  # This causes N+1
        unoptimized_queries = len(connection.queries) - start_queries
        
        # Optimized - should prevent N+1
        start_queries = len(connection.queries)
        users = User.objects.prefetch_related('team_memberships__team')[:5]
        for user in users:
            memberships = list(user.team_memberships.all())
            for membership in memberships:
                team_name = membership.team.name
        optimized_queries = len(connection.queries) - start_queries
        
        self.stdout.write(f'  Unoptimized: {unoptimized_queries} queries')
        self.stdout.write(f'  Optimized: {optimized_queries} queries')
        
        if unoptimized_queries > optimized_queries:
            improvement = unoptimized_queries - optimized_queries
            self.stdout.write(self.style.SUCCESS(f'  Improvement: {improvement} fewer queries'))
        else:
            self.stdout.write(self.style.WARNING('  No improvement detected'))

    def _analyze_index_usage(self):
        """Analyze database index usage"""
        self.stdout.write('\n=== Index Usage Analysis ===')
        
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                # SQLite doesn't have pg_stat_user_indexes, so we'll show basic info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
                indexes = cursor.fetchall()
                
                self.stdout.write(f'Found {len(indexes)} custom indexes:')
                for index in indexes[:10]:  # Show first 10
                    self.stdout.write(f'  • {index[0]}')
                    
            elif connection.vendor == 'postgresql':
                # PostgreSQL index usage stats
                cursor.execute("""
                    SELECT indexrelname, idx_tup_read, idx_tup_fetch 
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = 'public' AND indexrelname LIKE 'idx_%'
                    ORDER BY idx_tup_read DESC
                    LIMIT 10
                """)
                indexes = cursor.fetchall()
                
                self.stdout.write('Top 10 used indexes:')
                for idx_name, reads, fetches in indexes:
                    self.stdout.write(f'  • {idx_name}: {reads} reads, {fetches} fetches')

    def _test_query_optimizations(self):
        """Test query optimization strategies"""
        self.stdout.write('\n=== Query Optimization Testing ===')
        
        # Test optimized querysets from query_optimizer
        users_queryset = query_optimizer.get_optimized_user_queryset()
        teams_queryset = query_optimizer.get_optimized_team_queryset()
        
        self.stdout.write('Testing optimized querysets...')
        
        # Measure performance
        start_time = time.time()
        start_queries = len(connection.queries)
        
        # Execute optimized queries
        users = list(users_queryset[:10])
        teams = list(teams_queryset[:5])
        
        # Access related data to trigger queries
        for user in users:
            skills = list(user.user_skills.all())
            memberships = list(user.team_memberships.all())
        
        for team in teams:
            members = list(team.memberships.all())
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        duration = (end_time - start_time) * 1000  # Convert to ms
        query_count = end_queries - start_queries
        
        self.stdout.write(f'  Execution time: {duration:.2f}ms')
        self.stdout.write(f'  Query count: {query_count}')
        
        if query_count < 50:  # Arbitrary threshold
            self.stdout.write(self.style.SUCCESS('  Query count looks optimized'))
        else:
            self.stdout.write(self.style.WARNING('  High query count - may need optimization'))

    def _run_general_analysis(self):
        """Run general database analysis"""
        self.stdout.write('\n=== General Database Analysis ===')
        
        # Get table sizes
        with connection.cursor() as cursor:
            table_info = []
            
            tables = ['tps_users', 'tps_teams', 'tps_team_memberships', 
                     'tps_shift_instances', 'tps_assignments', 'tps_user_skills']
            
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cursor.fetchone()[0]
                    table_info.append((table, count))
                except:
                    table_info.append((table, 'Error'))
            
            self.stdout.write('Table row counts:')
            for table, count in table_info:
                self.stdout.write(f'  • {table}: {count}')
        
        # Generate optimization report
        report = query_optimizer.generate_query_optimization_report()
        
        self.stdout.write('\nOptimization Suggestions:')
        for suggestion in report['optimization_suggestions'][:5]:
            self.stdout.write(f'  • {suggestion}')
        
        # Cache recommendations
        cache_suggestions = query_optimizer.get_cache_optimization_suggestions()
        self.stdout.write('\nCache Optimization Suggestions:')
        for suggestion in cache_suggestions[:3]:
            self.stdout.write(f'  • {suggestion}')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Analysis complete!')
        self.stdout.write('Run with --test-n-plus-one to test N+1 query patterns')
        self.stdout.write('Run with --analyze-indexes to check index usage')
        self.stdout.write('Run with --test-optimizations to test query optimizations')