"""
TPS Database Optimization Management Command
Applies database performance and integrity optimizations
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.conf import settings


class Command(BaseCommand):
    help = 'Apply database optimizations for TPS (indexes, constraints, views)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be executed without making changes',
        )
        parser.add_argument(
            '--section',
            choices=['indexes', 'constraints', 'triggers', 'views', 'all'],
            default='all',
            help='Which optimization section to apply',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force application even on production database',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.section = options['section']
        self.force = options['force']
        
        # Safety check for production
        if not self.force and not settings.DEBUG:
            raise CommandError(
                "This command is disabled in production. Use --force to override, "
                "but ensure you have database backup first!"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'TPS Database Optimization - Section: {self.section}')
        )
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get database engine
        engine = connection.vendor
        self.stdout.write(f'Database engine: {engine}')
        
        # Load optimization script
        script_path = os.path.join(settings.BASE_DIR, 'database_optimization.sql')
        if not os.path.exists(script_path):
            raise CommandError(f'Optimization script not found: {script_path}')
        
        with open(script_path, 'r') as f:
            full_script = f.read()
        
        # Parse sections
        sections = self._parse_script_sections(full_script)
        
        # Apply optimizations
        if self.section == 'all':
            sections_to_apply = sections.keys()
        else:
            sections_to_apply = [self.section]
        
        for section_name in sections_to_apply:
            if section_name in sections:
                self._apply_section(section_name, sections[section_name], engine)
        
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS('Database optimization completed successfully!')
            )
        
    def _parse_script_sections(self, script):
        """Parse SQL script into sections"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in script.split('\n'):
            line = line.strip()
            
            # Check for section headers
            if line.startswith('-- =') and 'PERFORMANCE INDEXES' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'indexes'
                current_content = []
            elif line.startswith('-- =') and 'BUSINESS RULE CONSTRAINTS' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'constraints'
                current_content = []
            elif line.startswith('-- =') and 'DATA INTEGRITY TRIGGERS' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'triggers'
                current_content = []
            elif line.startswith('-- =') and 'QUERY OPTIMIZATION VIEWS' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'views'
                current_content = []
            elif line.startswith('-- =') and 'MAINTENANCE PROCEDURES' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'procedures'
                current_content = []
            elif current_section and line and not line.startswith('--'):
                current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _apply_section(self, section_name, section_content, engine):
        """Apply a specific section of optimizations"""
        self.stdout.write(f'\n{self.style.HTTP_INFO(f"Applying {section_name.upper()} optimizations...")}')
        
        # Skip PostgreSQL-only sections on SQLite
        if engine == 'sqlite' and section_name in ['triggers', 'procedures']:
            self.stdout.write(
                self.style.WARNING(f'Skipping {section_name} (PostgreSQL only)')
            )
            return
        
        statements = self._split_sql_statements(section_content)
        
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement:
                continue
                
            # Extract statement type for logging
            stmt_type = statement.split()[0].upper() if statement else 'UNKNOWN'
            
            if self.dry_run:
                self.stdout.write(f'  Would execute: {stmt_type} ...')
                continue
            
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(statement)
                self.stdout.write(f'  ✓ Applied: {stmt_type}')
            except Exception as e:
                # Some statements might fail if already exist (indexes, constraints)
                if any(keyword in str(e).lower() for keyword in ['already exists', 'duplicate', 'constraint', 'index']):
                    self.stdout.write(f'  ~ Skipped: {stmt_type} (already exists)')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed: {stmt_type} - {str(e)}')
                    )
                    if 'constraint' not in str(e).lower():
                        # Don't fail on constraint errors, just warn
                        raise CommandError(f'Failed to execute {stmt_type}: {e}')
    
    def _split_sql_statements(self, content):
        """Split SQL content into individual statements"""
        # Simple splitting by semicolon (outside of function definitions)
        statements = []
        current_statement = []
        in_function = False
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            # Detect function definitions
            if 'CREATE OR REPLACE FUNCTION' in line.upper():
                in_function = True
            elif line.upper().startswith('$$') and in_function:
                in_function = False
                current_statement.append(line)
                statements.append('\n'.join(current_statement))
                current_statement = []
                continue
            
            current_statement.append(line)
            
            # End of statement
            if line.endswith(';') and not in_function:
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add remaining content
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements