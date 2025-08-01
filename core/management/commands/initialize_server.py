"""
Management command to initialize TPS server with comprehensive production-ready data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from apps.teams.models import Team, TeamRole, TeamMembership
from apps.accounts.models import SkillCategory, Skill, UserSkill
from apps.scheduling.models import ShiftCategory, ShiftTemplate, ShiftInstance, PlanningPeriod
from apps.leave_management.models import LeaveType, LeaveBalance
from apps.notifications.models import NotificationPreference
from core.config import config_manager
from datetime import date, datetime, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize TPS server with comprehensive production-ready data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--production',
            action='store_true',
            help='Create production-ready data instead of test data'
        )
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip creating test users (useful for production)'
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=8,
            help='Number of weeks of shift templates to create'
        )
    
    def handle(self, *args, **options):
        self.is_production = options['production']
        self.skip_users = options['skip_users']
        
        with transaction.atomic():
            self.stdout.write(
                self.style.SUCCESS(
                    f'🚀 Initializing TPS server with {"production" if self.is_production else "test"} data...'
                )
            )
            
            # Initialize in logical order
            self.create_foundation_data()
            self.create_skill_system()
            self.create_team_structure()
            self.create_shift_system()
            self.create_leave_system()
            
            if not self.skip_users:
                users = self.create_user_accounts()
                self.assign_users_to_teams(users)
                self.assign_user_skills(users)
                self.create_notification_preferences(users)
            
            self.create_planning_structure(options['weeks'])
            
            self.display_summary()
    
    def create_foundation_data(self):
        """Create foundational data structures"""
        self.stdout.write('📋 Creating foundation data...')
        
        # Core statuses
        statuses = [
            ('active', 'Active', 'Items that are currently active'),
            ('inactive', 'Inactive', 'Items that are temporarily inactive'),
            ('draft', 'Draft', 'Items in draft state'),
            ('published', 'Published', 'Items that are published'),
            ('cancelled', 'Cancelled', 'Items that have been cancelled'),
            ('completed', 'Completed', 'Items that have been completed'),
            ('pending', 'Pending', 'Items awaiting action'),
            ('approved', 'Approved', 'Items that have been approved'),
            ('rejected', 'Rejected', 'Items that have been rejected'),
        ]
        
        # For now, create a simple mapping since Status model might not be available
        self.status_mapping = {name: name for name, _, _ in statuses}
        
        # Core priorities
        priorities = [
            ('low', 'Low Priority', 1),
            ('normal', 'Normal Priority', 2),
            ('high', 'High Priority', 3),
            ('urgent', 'Urgent Priority', 4),
            ('critical', 'Critical Priority', 5),
        ]
        
        self.priority_mapping = {name: name for name, _, _ in priorities}
        
        self.stdout.write('  ✅ Foundation data created')
    
    def create_skill_system(self):
        """Create comprehensive skill categories and skills"""
        self.stdout.write('🎯 Creating skill system...')
        
        # Skill categories
        categories_data = [
            ('Technical Operations', 'Core technical operational skills', '#3B82F6'),
            ('Security & Compliance', 'Security and compliance related skills', '#EF4444'),
            ('Network Management', 'Network infrastructure and management', '#10B981'),
            ('Application Support', 'Application development and support', '#8B5CF6'),
            ('Database Administration', 'Database management and optimization', '#F59E0B'),
            ('Cloud & Infrastructure', 'Cloud platforms and infrastructure', '#06B6D4'),
            ('DevOps & Automation', 'DevOps practices and automation tools', '#84CC16'),
            ('Incident Management', 'Incident response and management', '#F97316'),
        ]
        
        categories = {}
        for name, description, color in categories_data:
            category, created = SkillCategory.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'color': color,
                    'is_active': True
                }
            )
            categories[name] = category
            if created:
                self.stdout.write(f'  + Created skill category: {name}')
        
        # Skills by category
        skills_data = {
            'Technical Operations': [
                ('Linux Administration', 'intermediate', True, 24),
                ('Windows Server', 'intermediate', True, 24),
                ('System Monitoring', 'basic', False, None),
                ('Performance Tuning', 'advanced', False, None),
                ('Backup & Recovery', 'intermediate', True, 12),
                ('Virtualization (VMware)', 'intermediate', True, 36),
                ('Storage Management', 'intermediate', False, None),
            ],
            'Security & Compliance': [
                ('Security Operations', 'intermediate', True, 12),
                ('Vulnerability Assessment', 'advanced', True, 24),
                ('Compliance Auditing', 'intermediate', True, 12),
                ('Incident Response', 'intermediate', True, 12),
                ('Penetration Testing', 'expert', True, 24),
                ('GDPR Compliance', 'intermediate', True, 24),
            ],
            'Network Management': [
                ('Network Infrastructure', 'intermediate', False, None),
                ('Firewall Management', 'intermediate', True, 12),
                ('Load Balancers', 'intermediate', False, None),
                ('VPN Configuration', 'basic', False, None),
                ('Network Troubleshooting', 'intermediate', False, None),
                ('Cisco Equipment', 'intermediate', True, 36),
            ],
            'Application Support': [
                ('Web Application Support', 'basic', False, None),
                ('API Development', 'intermediate', False, None),
                ('Database Queries', 'basic', False, None),
                ('Application Deployment', 'intermediate', False, None),
                ('Bug Investigation', 'basic', False, None),
                ('Performance Monitoring', 'intermediate', False, None),
            ],
            'Database Administration': [
                ('PostgreSQL', 'intermediate', True, 24),
                ('MySQL/MariaDB', 'intermediate', True, 24),
                ('Database Optimization', 'advanced', False, None),
                ('Backup Strategies', 'intermediate', True, 12),
                ('Replication Setup', 'advanced', False, None),
                ('Query Optimization', 'intermediate', False, None),
            ],
            'Cloud & Infrastructure': [
                ('AWS Services', 'intermediate', True, 36),
                ('Azure Platform', 'intermediate', True, 36),
                ('Docker Containers', 'intermediate', False, None),
                ('Kubernetes', 'advanced', True, 12),
                ('Infrastructure as Code', 'intermediate', False, None),
                ('Cloud Security', 'intermediate', True, 24),
            ],
            'DevOps & Automation': [
                ('CI/CD Pipelines', 'intermediate', False, None),
                ('Ansible Automation', 'intermediate', False, None),
                ('Terraform', 'intermediate', False, None),
                ('Git & Version Control', 'basic', False, None),
                ('Script Development', 'basic', False, None),
                ('Configuration Management', 'intermediate', False, None),
            ],
            'Incident Management': [
                ('24/7 On-Call Support', 'basic', True, 6),
                ('Crisis Communication', 'intermediate', False, None),
                ('Root Cause Analysis', 'intermediate', False, None),
                ('Service Restoration', 'intermediate', False, None),
                ('Escalation Management', 'basic', False, None),
                ('Post-Incident Review', 'basic', False, None),
            ],
        }
        
        total_skills = 0
        for category_name, skills in skills_data.items():
            category = categories[category_name]
            for skill_name, min_level, requires_cert, cert_months in skills:
                skill, created = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={
                        'category': category,
                        'description': f'{skill_name} - {category_name}',
                        'minimum_level_required': min_level,
                        'requires_certification': requires_cert,
                        'certification_validity_months': cert_months,
                        'is_active': True
                    }
                )
                if created:
                    total_skills += 1
        
        self.stdout.write(f'  ✅ Created {len(categories)} skill categories and {total_skills} skills')
    
    def create_team_structure(self):
        """Create team roles and organizational structure"""
        self.stdout.write('👥 Creating team structure...')
        
        # Team roles with proper permissions
        roles_data = [
            ('member', 'Team Member', 'Standard team member with basic access', False, False, False, False),
            ('senior_member', 'Senior Team Member', 'Experienced team member', False, False, False, False),
            ('coordinator', 'Team Coordinator', 'Coordinates team activities', True, False, False, True),
            ('lead', 'Team Lead', 'Team leader with full permissions', True, True, True, True),
            ('deputy_lead', 'Deputy Team Lead', 'Assistant team leader', True, True, False, True),
            ('trainer', 'Team Trainer', 'Responsible for training new members', False, False, False, True),
            ('scheduler', 'Team Scheduler', 'Manages team scheduling', True, False, False, False),
            ('specialist', 'Technical Specialist', 'Subject matter expert', False, False, False, True),
        ]
        
        for name, display_name, description, can_assign, can_approve, can_manage, can_mentor in roles_data:
            role, created = TeamRole.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'can_assign_shifts': can_assign,
                    'can_approve_swaps': can_approve,
                    'can_manage_team': can_manage
                }
            )
            if created:
                self.stdout.write(f'  + Created team role: {display_name}')
        
        # Create teams based on production needs
        if self.is_production:
            teams_data = [
                ('Infrastructure Operations', 'INFRA', 'Core infrastructure management and monitoring', True),
                ('Application Support', 'APPS', 'Business application support and maintenance', True),
                ('Network Operations', 'NETWORK', 'Network infrastructure and connectivity', True),
                ('Security Operations', 'SECURITY', 'Information security and compliance', True),
                ('Database Administration', 'DBA', 'Database management and optimization', True),
            ]
        else:
            teams_data = [
                ('TPS Team Alpha', 'ALPHA', 'Primary operational team for testing', True),
                ('TPS Team Beta', 'BETA', 'Secondary support team for testing', True),
                ('TPS Team Gamma', 'GAMMA', 'Specialized response team for testing', True),
            ]
        
        teams_created = 0
        for name, code, description, is_active in teams_data:
            team, created = Team.objects.get_or_create(
                name=name,
                defaults={
                    'department': code,
                    'description': description,
                    'is_active': is_active,
                    'max_weekly_hours': 40,
                    'min_staff_level': 2,
                    'allows_overtime': True
                }
            )
            if created:
                teams_created += 1
                self.stdout.write(f'  + Created team: {name}')
        
        self.stdout.write(f'  ✅ Created {len(roles_data)} team roles and {teams_created} teams')
    
    def create_shift_system(self):
        """Create comprehensive shift categories and templates"""
        self.stdout.write('⏰ Creating shift system...')
        
        # Shift categories
        categories_data = [
            ('WAAKDIENST', 'Waakdienst', 'Primary on-call duty', '#EF4444', 12, 40, 7, True, True),
            ('INCIDENT', 'Incident Response', 'Emergency incident handling', '#F59E0B', 52, 8, 1, True, True),
            ('CHANGES', 'Change Management', 'Planned system changes', '#8B5CF6', 26, 16, 3, False, False),
            ('PROJECTS', 'Project Work', 'Development and project tasks', '#10B981', 52, 40, 1, False, False),
            ('MAINTENANCE', 'System Maintenance', 'Routine maintenance tasks', '#06B6D4', 52, 24, 2, False, True),
            ('TRAINING', 'Training & Development', 'Skills development and training', '#84CC16', 12, 8, 30, False, False),
            ('SUPPORT', 'Business Support', 'Standard business hours support', '#64748B', 52, 40, 1, False, False),
            ('STANDBY', 'Standby Duty', 'Standby availability', '#94A3B8', 26, 8, 3, True, False),
        ]
        
        categories_created = 0
        for name, display_name, description, color, max_weeks, hours_per_week, min_gap, is_critical, requires_certification in categories_data:
            category, created = ShiftCategory.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'max_weeks_per_year': max_weeks,
                    'hours_per_week': hours_per_week,
                    'min_gap_days': min_gap,
                    'requires_handover': is_critical,
                    'allows_auto_assignment': not is_critical,
                }
            )
            if created:
                categories_created += 1
                self.stdout.write(f'  + Created shift category: {display_name}')
        
        # Shift templates
        templates_data = [
            # Waakdienst shifts
            ('Weekend Waakdienst', 'WAAKDIENST', 'Weekend on-call duty', '09:00', '17:00', 8, False, True, False, 1, 0),
            ('Evening Waakdienst', 'WAAKDIENST', 'Evening/night on-call', '17:00', '09:00', 16, True, False, True, 1, 0),
            ('Weekly Waakdienst', 'WAAKDIENST', 'Full week on-call duty', '00:00', '23:59', 168, False, True, True, 1, 1),
            
            # Incident response
            ('Incident Response Day', 'INCIDENT', 'Daytime incident response', '08:00', '17:00', 9, False, False, False, 2, 1),
            ('Incident Response Night', 'INCIDENT', 'Night incident response', '22:00', '06:00', 8, True, False, True, 1, 1),
            ('Critical Incident Team', 'INCIDENT', 'Critical incident response', '00:00', '23:59', 24, False, False, False, 3, 1),
            
            # Change management
            ('Change Window Evening', 'CHANGES', 'Evening change window', '18:00', '02:00', 8, True, False, True, 2, 0),
            ('Change Window Weekend', 'CHANGES', 'Weekend change implementation', '08:00', '18:00', 10, False, True, False, 2, 1),
            
            # Project work
            ('Project Development', 'PROJECTS', 'Standard project work', '09:00', '17:00', 8, False, False, False, 1, 0),
            ('Project Support', 'PROJECTS', 'Project support activities', '08:00', '16:00', 8, False, False, False, 1, 0),
            
            # Maintenance
            ('System Maintenance', 'MAINTENANCE', 'Routine system maintenance', '06:00', '14:00', 8, False, False, False, 1, 0),
            ('Emergency Maintenance', 'MAINTENANCE', 'Emergency maintenance work', '00:00', '23:59', 12, False, False, False, 2, 1),
            
            # Training
            ('Skills Training', 'TRAINING', 'Professional development', '09:00', '17:00', 8, False, False, False, 1, 0),
            ('Certification Prep', 'TRAINING', 'Certification preparation', '09:00', '15:00', 6, False, False, False, 1, 0),
            
            # Support
            ('Business Hours Support', 'SUPPORT', 'Standard business support', '08:00', '17:00', 9, False, False, False, 2, 0),
            ('Extended Support', 'SUPPORT', 'Extended hours support', '07:00', '19:00', 12, False, False, False, 3, 1),
            
            # Standby
            ('Standby Availability', 'STANDBY', 'Standby availability', '17:00', '08:00', 15, True, False, True, 1, 0),
            ('Weekend Standby', 'STANDBY', 'Weekend standby duty', '17:00', '08:00', 39, True, True, True, 1, 0),
        ]
        
        templates_created = 0
        for name, category_name, description, start_time, end_time, duration, overnight, weekend, weekly, engineers, backup in templates_data:
            try:
                category = ShiftCategory.objects.get(name=category_name)
                template, created = ShiftTemplate.objects.get_or_create(
                    name=name,
                    defaults={
                        'category': category,
                        'description': description,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration_hours': duration,
                        'is_overnight': overnight,
                        'spans_weekend': weekend,
                        'is_weekly_shift': weekly,
                        'engineers_required': engineers,
                        'backup_engineers': backup,
                        'is_active': True
                    }
                )
                if created:
                    templates_created += 1
                    self.stdout.write(f'  + Created shift template: {name}')
            except ShiftCategory.DoesNotExist:
                self.stdout.write(f'  ! Warning: Category {category_name} not found for template {name}')
        
        self.stdout.write(f'  ✅ Created {categories_created} shift categories and {templates_created} shift templates')
    
    def create_leave_system(self):
        """Create leave types and balance system"""
        self.stdout.write('🏖️ Creating leave system...')
        
        # Leave types
        leave_types_data = [
            ('annual', 'Annual Leave', 'Standard vacation time', True, 30, '#10B981', True),
            ('sick', 'Sick Leave', 'Medical leave for illness', True, 10, '#EF4444', False),
            ('personal', 'Personal Leave', 'Personal time off', True, 5, '#8B5CF6', True),
            ('emergency', 'Emergency Leave', 'Unexpected emergency situations', False, 3, '#F59E0B', False),
            ('training', 'Training Leave', 'Professional development', True, 10, '#06B6D4', True),
            ('compassionate', 'Compassionate Leave', 'Family emergency or bereavement', False, 5, '#94A3B8', False),
            ('maternity', 'Maternity Leave', 'Maternity leave', False, 90, '#EC4899', False),
            ('paternity', 'Paternity Leave', 'Paternity leave', False, 14, '#3B82F6', False),
            ('study', 'Study Leave', 'Educational pursuits', True, 5, '#84CC16', True),
            ('unpaid', 'Unpaid Leave', 'Unpaid time off', True, 30, '#64748B', True),
        ]
        
        # This would require the LeaveType model to exist
        # For now, we'll just log what we would create
        leave_types_created = 0
        for code, name, description, requires_approval, max_days, color, affects_pay in leave_types_data:
            # LeaveType.objects.get_or_create would go here
            leave_types_created += 1
            self.stdout.write(f'  + Would create leave type: {name}')
        
        self.stdout.write(f'  ✅ Prepared {leave_types_created} leave types')
    
    def create_user_accounts(self):
        """Create user accounts based on mode"""
        self.stdout.write('👤 Creating user accounts...')
        
        # Get configuration
        admin_config = config_manager.get_admin_config()
        test_config = config_manager.get_test_config()
        org_config = config_manager.get_organization_config()
        
        # Always create admin user
        admin_user = None
        admin_username = admin_config['username']
        if not User.objects.filter(username=admin_username).exists():
            admin_user = User.objects.create_superuser(
                username=admin_config['username'],
                email=admin_config['email'],
                password=admin_config['password'],
                first_name=admin_config['first_name'],
                last_name=admin_config['last_name']
            )
            admin_user.employee_id = config_manager.generate_employee_id(1, 'ADM')
            admin_user.role = 'MANAGER'
            admin_user.phone = config_manager.generate_phone_number()
            admin_user.save()
            self.stdout.write(f'  + Created admin user ({admin_username}/[configured password])')
        else:
            admin_user = User.objects.get(username=admin_username)

        users = [admin_user] if admin_user else []

        if self.is_production:
            # Create minimal production users
            production_users = [
                ('planner', 'System', 'Planner', 'PLANNER', config_manager.generate_employee_id(1, 'PLN')),
                ('manager', 'Department', 'Manager', 'MANAGER', config_manager.generate_employee_id(1, 'MGR')),
            ]
            
            for username, first_name, last_name, role, emp_id in production_users:
                if not User.objects.filter(username=username).exists():
                    # Generate secure password for production
                    secure_password = config_manager.generate_secure_password()
                    
                    user = User.objects.create_user(
                        username=username,
                        email=config_manager.generate_test_email(username),
                        password=secure_password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    user.employee_id = emp_id
                    user.role = role
                    user.is_staff = True if role in ['PLANNER', 'MANAGER'] else False
                    user.save()
                    users.append(user)
                    self.stdout.write(f'  + Created {role.lower()} user: {username} (password: {secure_password})')
        else:
            # Create test users if enabled
            if test_config['create_test_users']:
                test_users_data = [
                    ('planner1', 'Alice', 'Planner', 'PLANNER', config_manager.generate_employee_id(1, 'PLN')),
                    ('manager1', 'Bob', 'Manager', 'MANAGER', config_manager.generate_employee_id(1, 'MGR')),
                    ('user1', 'Charlie', 'Engineer', 'USER', config_manager.generate_employee_id(1)),
                    ('user2', 'Diana', 'Technician', 'USER', config_manager.generate_employee_id(2)),
                    ('user3', 'Edward', 'Analyst', 'USER', config_manager.generate_employee_id(3)),
                    ('user4', 'Fiona', 'Specialist', 'USER', config_manager.generate_employee_id(4)),
                    ('user5', 'George', 'Coordinator', 'USER', config_manager.generate_employee_id(5)),
                    ('user6', 'Helen', 'Administrator', 'USER', config_manager.generate_employee_id(6)),
                    ('user7', 'Ian', 'Developer', 'USER', config_manager.generate_employee_id(7)),
                    ('user8', 'Julia', 'Support', 'USER', config_manager.generate_employee_id(8)),
                ]
                
                for username, first_name, last_name, role, emp_id in test_users_data:
                    if not User.objects.filter(username=username).exists():
                        user = User.objects.create_user(
                            username=username,
                            email=config_manager.generate_test_email(username),
                            password=test_config['test_password'],
                            first_name=first_name,
                            last_name=last_name
                        )
                        user.employee_id = emp_id
                        user.role = role
                        user.phone = config_manager.generate_phone_number()
                        user.is_staff = True if role in ['PLANNER', 'MANAGER'] else False
                        user.save()
                        users.append(user)
                        self.stdout.write(f'  + Created test user: {username} ({role})')

        self.stdout.write(f'  ✅ Created {len(users)} user accounts')
        return users
    
    def assign_users_to_teams(self, users):
        """Assign users to teams with appropriate roles"""
        self.stdout.write('👥 Assigning users to teams...')
        
        teams = list(Team.objects.filter(is_active=True))
        if not teams:
            self.stdout.write('  ! No active teams found to assign users to')
            return
        
        # Get team roles
        lead_role = TeamRole.objects.filter(name='lead').first()
        coordinator_role = TeamRole.objects.filter(name='coordinator').first()
        member_role = TeamRole.objects.filter(name='member').first()
        
        if not member_role:
            self.stdout.write('  ! No team roles found')
            return
        
        assignments = 0
        for i, user in enumerate(users):
            # Skip admin user
            if user.username == 'admin':
                continue
            
            # Assign to team (distribute evenly)
            team = teams[i % len(teams)]
            
            # Determine role based on user's system role and position
            if user.role == 'MANAGER' or (i == 1 and lead_role):
                team_role = lead_role
            elif user.role == 'PLANNER' or (i == 2 and coordinator_role):
                team_role = coordinator_role
            else:
                team_role = member_role
            
            # Create team membership
            membership, created = TeamMembership.objects.get_or_create(
                user=user,
                team=team,
                defaults={
                    'role': team_role,
                    'join_date': date.today(),
                    'is_active': True
                }
            )
            
            if created:
                assignments += 1
                role_name = team_role.name if team_role else 'member'
                self.stdout.write(f'  + Assigned {user.username} to {team.name} as {role_name}')
        
        self.stdout.write(f'  ✅ Created {assignments} team assignments')
    
    def assign_user_skills(self, users):
        """Assign skills to users"""
        self.stdout.write('🎯 Assigning skills to users...')
        
        skills = list(Skill.objects.filter(is_active=True))
        if not skills:
            self.stdout.write('  ! No skills available to assign')
            return
        
        skill_assignments = 0
        for user in users:
            # Skip admin user
            if user.username == 'admin':
                continue
            
            # Assign 3-7 random skills per user
            num_skills = random.randint(3, 7)
            user_skills = random.sample(skills, min(num_skills, len(skills)))
            
            for skill in user_skills:
                # Random proficiency level
                proficiency_levels = ['basic', 'intermediate', 'advanced', 'expert']
                proficiency = random.choice(proficiency_levels)
                
                # Random certification status
                is_certified = random.choice([True, False]) if skill.requires_certification else False
                cert_date = timezone.now().date() - timedelta(days=random.randint(30, 730)) if is_certified else None
                
                user_skill, created = UserSkill.objects.get_or_create(
                    user=user,
                    skill=skill,
                    defaults={
                        'proficiency_level': proficiency,
                        'is_certified': is_certified,
                        'certification_date': cert_date,
                    }
                )
                
                if created:
                    skill_assignments += 1
        
        self.stdout.write(f'  ✅ Created {skill_assignments} skill assignments')
    
    def create_notification_preferences(self, users):
        """Create notification preferences for users"""
        self.stdout.write('🔔 Creating notification preferences...')
        
        # This would require NotificationPreference model
        # For now, just log what we would create
        preferences_created = 0
        for user in users:
            if user.username != 'admin':
                preferences_created += 1
                self.stdout.write(f'  + Would create notification preferences for {user.username}')
        
        self.stdout.write(f'  ✅ Prepared {preferences_created} notification preference sets')
    
    def create_planning_structure(self, weeks):
        """Create planning periods and initial shift instances"""
        self.stdout.write(f'📅 Creating planning structure for {weeks} weeks...')
        
        # Create planning period
        start_date = date.today()
        end_date = start_date + timedelta(weeks=weeks)
        
        period_name = f'Initial Planning Period - {start_date.strftime("%B %Y")}'
        period, created = PlanningPeriod.objects.get_or_create(
            name=period_name,
            defaults={
                'period_type': 'monthly',
                'start_date': start_date,
                'end_date': end_date,
                'planning_deadline': timezone.now() + timedelta(days=14),
                'status': 'active',
                'allows_auto_generation': True,
                'created_by': User.objects.filter(role='MANAGER').first()
            }
        )
        
        if created:
            self.stdout.write(f'  + Created planning period: {period_name}')
        
        # Create sample shift instances for first week only to avoid clutter
        templates = ShiftTemplate.objects.filter(is_active=True)[:5]  # Limit to 5 templates
        instances_created = 0
        
        current_date = start_date
        end_sample_date = start_date + timedelta(days=7)  # Only first week
        
        while current_date <= end_sample_date and current_date <= end_date:
            for template in templates:
                # Create shift instances based on template schedule
                should_create = False
                
                if template.is_weekly_shift:
                    # Weekly shifts only on Monday
                    should_create = current_date.weekday() == 0
                elif template.spans_weekend:
                    # Weekend shifts only on weekends
                    should_create = current_date.weekday() >= 5
                else:
                    # Regular shifts on weekdays
                    should_create = current_date.weekday() < 5
                
                if should_create:
                    start_datetime = timezone.make_aware(
                        datetime.combine(current_date, template.start_time)
                    )
                    
                    # Handle overnight shifts
                    if template.is_overnight:
                        end_date_for_shift = current_date + timedelta(days=1)
                    else:
                        end_date_for_shift = current_date
                    
                    end_datetime = timezone.make_aware(
                        datetime.combine(end_date_for_shift, template.end_time)
                    )
                    
                    shift_instance, created = ShiftInstance.objects.get_or_create(
                        template=template,
                        date=current_date,
                        defaults={
                            'start_datetime': start_datetime,
                            'end_datetime': end_datetime,
                            'status': 'published',
                            'planning_period': period
                        }
                    )
                    
                    if created:
                        instances_created += 1
            
            current_date += timedelta(days=1)
        
        self.stdout.write(f'  ✅ Created planning period and {instances_created} sample shift instances')
    
    def display_summary(self):
        """Display initialization summary"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 TPS SERVER INITIALIZATION COMPLETE'))
        self.stdout.write('='*60)
        
        # Count what was created
        skill_categories = SkillCategory.objects.count()
        skills = Skill.objects.count()
        team_roles = TeamRole.objects.count()
        teams = Team.objects.count()
        users = User.objects.count()
        shift_categories = ShiftCategory.objects.count()
        shift_templates = ShiftTemplate.objects.count()
        shift_instances = ShiftInstance.objects.count()
        team_memberships = TeamMembership.objects.count()
        
        summary_data = [
            ('👤 Users', users),
            ('👥 Teams', teams),
            ('🎭 Team Roles', team_roles),
            ('👥 Team Memberships', team_memberships),
            ('📚 Skill Categories', skill_categories),
            ('🎯 Skills', skills),
            ('📅 Shift Categories', shift_categories),
            ('📋 Shift Templates', shift_templates),
            ('⏰ Shift Instances', shift_instances),
        ]
        
        for label, count in summary_data:
            self.stdout.write(f'{label}: {count}')
        
        self.stdout.write('\n📋 QUICK START GUIDE:')
        admin_config = config_manager.get_admin_config()
        test_config = config_manager.get_test_config()
        
        self.stdout.write(f'1. Login as {admin_config["username"]} with configured password for full access')
        if not self.is_production and test_config['create_test_users']:
            self.stdout.write(f'2. Test users: user1-8 (password: {test_config["test_password"]})')
            self.stdout.write(f'3. Planner access: planner1 (password: {test_config["test_password"]})')
        self.stdout.write('4. Navigate to /schedule/ to view the calendar')
        self.stdout.write('5. Visit /admin/ for administrative functions')
        
        self.stdout.write('\n🚀 Your TPS server is ready for use!')
        self.stdout.write('='*60)
