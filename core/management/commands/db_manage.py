"""
TPS Database Backup and Monitoring Utilities
Provides backup, restore, and health monitoring capabilities
"""
import os
import subprocess
import datetime
import json
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings
from django.core.management import call_command
import tempfile

logger = logging.getLogger('tps.database')


class Command(BaseCommand):
    help = 'Database backup, restore, and health monitoring for TPS'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['backup', 'restore', 'health', 'analyze', 'vacuum'],
            help='Action to perform'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Backup file path (for restore operation)'
        )
        parser.add_argument(
            '--format',
            choices=['sql', 'json', 'custom'],
            default='sql',
            help='Backup format'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup file'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Output directory for backups'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'backup':
            self._create_backup(options)
        elif action == 'restore':
            self._restore_backup(options)
        elif action == 'health':
            self._check_health()
        elif action == 'analyze':
            self._analyze_database()
        elif action == 'vacuum':
            self._vacuum_database()

    def _create_backup(self, options):
        """Create database backup"""
        engine = connection.vendor
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure backup directory exists
        backup_dir = Path(options['output_dir'])
        backup_dir.mkdir(exist_ok=True)
        
        if engine == 'sqlite':
            self._backup_sqlite(backup_dir, timestamp, options)
        elif engine == 'postgresql':
            self._backup_postgresql(backup_dir, timestamp, options)
        else:
            raise CommandError(f'Backup not supported for {engine}')

    def _backup_sqlite(self, backup_dir, timestamp, options):
        """Backup SQLite database"""
        db_path = settings.DATABASES['default']['NAME']
        backup_filename = f'tps_backup_{timestamp}.sqlite3'
        backup_path = backup_dir / backup_filename
        
        self.stdout.write(f'Creating SQLite backup: {backup_path}')
        
        try:
            # Simple file copy for SQLite
            import shutil
            shutil.copy2(db_path, backup_path)
            
            # Create metadata file
            metadata = self._create_backup_metadata()
            metadata_path = backup_dir / f'tps_backup_{timestamp}.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            # Compress if requested
            if options['compress']:
                self._compress_backup(backup_path)
            
            self.stdout.write(
                self.style.SUCCESS(f'SQLite backup completed: {backup_path}')
            )
            
        except Exception as e:
            raise CommandError(f'Backup failed: {e}')

    def _backup_postgresql(self, backup_dir, timestamp, options):
        """Backup PostgreSQL database"""
        db_config = settings.DATABASES['default']
        backup_filename = f'tps_backup_{timestamp}.sql'
        backup_path = backup_dir / backup_filename
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', db_config.get('HOST', 'localhost'),
            '--port', str(db_config.get('PORT', 5432)),
            '--username', db_config['USER'],
            '--dbname', db_config['NAME'],
            '--verbose',
            '--no-password',
            '--file', str(backup_path)
        ]
        
        if options['format'] == 'custom':
            cmd.extend(['--format', 'custom'])
            backup_filename = backup_filename.replace('.sql', '.dump')
            backup_path = backup_dir / backup_filename
            cmd[-1] = str(backup_path)
        
        self.stdout.write(f'Creating PostgreSQL backup: {backup_path}')
        
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise CommandError(f'pg_dump failed: {result.stderr}')
            
            # Create metadata file
            metadata = self._create_backup_metadata()
            metadata_path = backup_dir / f'tps_backup_{timestamp}.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            # Compress if requested
            if options['compress']:
                self._compress_backup(backup_path)
            
            self.stdout.write(
                self.style.SUCCESS(f'PostgreSQL backup completed: {backup_path}')
            )
            
        except Exception as e:
            raise CommandError(f'Backup failed: {e}')

    def _restore_backup(self, options):
        """Restore database from backup"""
        backup_file = options.get('file')
        if not backup_file:
            raise CommandError('--file argument is required for restore')
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise CommandError(f'Backup file not found: {backup_path}')
        
        engine = connection.vendor
        
        # Safety confirmation
        if not settings.DEBUG:
            confirm = input('This will overwrite the production database. Continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Restore cancelled')
                return
        
        if engine == 'sqlite':
            self._restore_sqlite(backup_path)
        elif engine == 'postgresql':
            self._restore_postgresql(backup_path)
        else:
            raise CommandError(f'Restore not supported for {engine}')

    def _restore_sqlite(self, backup_path):
        """Restore SQLite database"""
        db_path = settings.DATABASES['default']['NAME']
        
        self.stdout.write(f'Restoring SQLite database from: {backup_path}')
        
        try:
            import shutil
            shutil.copy2(backup_path, db_path)
            self.stdout.write(self.style.SUCCESS('SQLite restore completed'))
        except Exception as e:
            raise CommandError(f'Restore failed: {e}')

    def _restore_postgresql(self, backup_path):
        """Restore PostgreSQL database"""
        db_config = settings.DATABASES['default']
        
        # Build psql command
        cmd = [
            'psql',
            '--host', db_config.get('HOST', 'localhost'),
            '--port', str(db_config.get('PORT', 5432)),
            '--username', db_config['USER'],
            '--dbname', db_config['NAME'],
            '--file', str(backup_path)
        ]
        
        self.stdout.write(f'Restoring PostgreSQL database from: {backup_path}')
        
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise CommandError(f'Restore failed: {result.stderr}')
            
            self.stdout.write(self.style.SUCCESS('PostgreSQL restore completed'))
            
        except Exception as e:
            raise CommandError(f'Restore failed: {e}')

    def _check_health(self):
        """Perform database health check"""
        self.stdout.write('Performing database health check...')
        
        health_report = {
            'timestamp': datetime.datetime.now(),
            'database_engine': connection.vendor,
            'checks': {}
        }
        
        # Basic connectivity check
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                health_report['checks']['connectivity'] = {'status': 'OK', 'message': 'Database connection successful'}
        except Exception as e:
            health_report['checks']['connectivity'] = {'status': 'ERROR', 'message': str(e)}
        
        # Table integrity check
        try:
            table_count = self._count_tables()
            health_report['checks']['tables'] = {
                'status': 'OK' if table_count > 0 else 'WARNING',
                'count': table_count,
                'message': f'Found {table_count} tables'
            }
        except Exception as e:
            health_report['checks']['tables'] = {'status': 'ERROR', 'message': str(e)}
        
        # Data integrity checks
        try:
            integrity_issues = self._check_data_integrity()
            health_report['checks']['data_integrity'] = {
                'status': 'OK' if not integrity_issues else 'WARNING',
                'issues': integrity_issues
            }
        except Exception as e:
            health_report['checks']['data_integrity'] = {'status': 'ERROR', 'message': str(e)}
        
        # Performance checks
        try:
            perf_stats = self._get_performance_stats()
            health_report['checks']['performance'] = {
                'status': 'OK',
                'stats': perf_stats
            }
        except Exception as e:
            health_report['checks']['performance'] = {'status': 'ERROR', 'message': str(e)}
        
        # Display results
        self._display_health_report(health_report)

    def _analyze_database(self):
        """Analyze database for optimization opportunities"""
        self.stdout.write('Analyzing database for optimization opportunities...')
        
        analysis = {
            'timestamp': datetime.datetime.now(),
            'table_stats': self._get_table_statistics(),
            'index_usage': self._analyze_index_usage(),
            'query_performance': self._analyze_query_performance(),
            'recommendations': []
        }
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        # Display analysis
        self._display_analysis_report(analysis)

    def _vacuum_database(self):
        """Vacuum database to reclaim space and update statistics"""
        engine = connection.vendor
        
        if engine == 'sqlite':
            self.stdout.write('Running SQLite VACUUM...')
            with connection.cursor() as cursor:
                cursor.execute('VACUUM')
                cursor.execute('ANALYZE')
        elif engine == 'postgresql':
            self.stdout.write('Running PostgreSQL VACUUM ANALYZE...')
            with connection.cursor() as cursor:
                cursor.execute('VACUUM ANALYZE')
        
        self.stdout.write(self.style.SUCCESS('Database vacuum completed'))

    def _create_backup_metadata(self):
        """Create backup metadata"""
        return {
            'timestamp': datetime.datetime.now(),
            'database_engine': connection.vendor,
            'django_version': __import__('django').get_version(),
            'migration_status': self._get_migration_status(),
            'table_counts': self._get_table_counts()
        }

    def _compress_backup(self, backup_path):
        """Compress backup file"""
        import gzip
        import shutil
        
        compressed_path = str(backup_path) + '.gz'
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_path.unlink()
        return compressed_path

    def _count_tables(self):
        """Count database tables"""
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            elif connection.vendor == 'postgresql':
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            return cursor.fetchone()[0]

    def _check_data_integrity(self):
        """Check data integrity"""
        issues = []
        
        # Check for orphaned records
        try:
            with connection.cursor() as cursor:
                # Example: Check for assignments without valid users
                cursor.execute("""
                    SELECT COUNT(*) FROM tps_assignments a 
                    LEFT JOIN tps_users u ON a.user_id = u.id 
                    WHERE u.id IS NULL
                """)
                orphaned_assignments = cursor.fetchone()[0]
                if orphaned_assignments > 0:
                    issues.append(f'{orphaned_assignments} orphaned assignments found')
        except:
            pass
        
        return issues

    def _get_performance_stats(self):
        """Get performance statistics"""
        stats = {}
        
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    # Get query statistics if pg_stat_statements is available
                    cursor.execute("""
                        SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'
                    """)
                    if cursor.fetchone()[0] > 0:
                        cursor.execute("""
                            SELECT 
                                calls,
                                total_exec_time,
                                mean_exec_time
                            FROM pg_stat_statements 
                            WHERE query LIKE '%tps_%'
                            ORDER BY mean_exec_time DESC 
                            LIMIT 5
                        """)
                        stats['slow_queries'] = cursor.fetchall()
        except:
            pass
        
        return stats

    def _get_table_statistics(self):
        """Get table statistics"""
        stats = {}
        
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            n_tup_ins,
                            n_tup_upd,
                            n_tup_del,
                            n_live_tup,
                            n_dead_tup
                        FROM pg_stat_user_tables
                        WHERE schemaname = 'public'
                        ORDER BY n_live_tup DESC
                    """)
                    stats['table_activity'] = cursor.fetchall()
        except:
            pass
        
        return stats

    def _analyze_index_usage(self):
        """Analyze index usage"""
        usage = {}
        
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT 
                            indexrelname,
                            idx_tup_read,
                            idx_tup_fetch
                        FROM pg_stat_user_indexes
                        WHERE schemaname = 'public'
                        ORDER BY idx_tup_read DESC
                    """)
                    usage['index_stats'] = cursor.fetchall()
        except:
            pass
        
        return usage

    def _analyze_query_performance(self):
        """Analyze query performance"""
        performance = {}
        
        # This would integrate with the QueryOptimizer service
        from core.services.query_optimizer import query_optimizer
        performance = query_optimizer.generate_query_optimization_report()
        
        return performance

    def _generate_recommendations(self, analysis):
        """Generate optimization recommendations"""
        recommendations = []
        
        # Add recommendations based on analysis
        recommendations.append("Run database optimization command: python manage.py optimize_database")
        recommendations.append("Consider adding indexes for frequently queried fields")
        recommendations.append("Monitor query performance regularly")
        recommendations.append("Schedule regular database maintenance")
        
        return recommendations

    def _get_migration_status(self):
        """Get Django migration status"""
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return {'pending_migrations': len(plan)}
        except:
            return {'error': 'Could not determine migration status'}

    def _get_table_counts(self):
        """Get row counts for major tables"""
        counts = {}
        tables = ['tps_users', 'tps_shift_instances', 'tps_assignments', 'tps_teams']
        
        try:
            with connection.cursor() as cursor:
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    counts[table] = cursor.fetchone()[0]
        except:
            pass
        
        return counts

    def _display_health_report(self, report):
        """Display health check report"""
        self.stdout.write('\n=== DATABASE HEALTH REPORT ===')
        self.stdout.write(f"Timestamp: {report['timestamp']}")
        self.stdout.write(f"Database Engine: {report['database_engine']}")
        
        for check_name, check_result in report['checks'].items():
            status = check_result['status']
            style = self.style.SUCCESS if status == 'OK' else (
                self.style.WARNING if status == 'WARNING' else self.style.ERROR
            )
            self.stdout.write(f"{check_name.title()}: {style(status)}")
            if 'message' in check_result:
                self.stdout.write(f"  {check_result['message']}")

    def _display_analysis_report(self, analysis):
        """Display analysis report"""
        self.stdout.write('\n=== DATABASE ANALYSIS REPORT ===')
        self.stdout.write(f"Timestamp: {analysis['timestamp']}")
        
        if analysis['recommendations']:
            self.stdout.write('\nRecommendations:')
            for rec in analysis['recommendations']:
                self.stdout.write(f"  • {rec}")