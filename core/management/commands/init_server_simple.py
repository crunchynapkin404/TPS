"""
Management command to initialize TPS server with core data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from apps.teams.models import Team, TeamRole, TeamMembership
from apps.accounts.models import SkillCategory, Skill, UserSkill
from apps.scheduling.models import ShiftCategory, ShiftTemplate, ShiftInstance, PlanningPeriod
from core.config import config_manager
from datetime import date, datetime, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize TPS server with essential data for immediate use'

    def add_arguments(self, parser):
        parser.add_argument(
            '--production',
            action='store_true',
            help='Create minimal production data instead of test data',
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Initializing TPS server with test data...')
        
        with transaction.atomic():
            try:
                # Create core system data
                self.create_team_roles()
                self.create_teams()
                self.create_skill_system()
                self.create_shift_system()
                self.create_users(production=options['production'])
                
                self.stdout.write(self.style.SUCCESS('✅ TPS server initialization complete!'))
                self.stdout.write('🌟 You can now log in with:')
                admin_config = config_manager.get_admin_config()
                if options['production']:
                    self.stdout.write(f'   Username: manager  Password: [generated secure password]')
                else:
                    test_config = config_manager.get_test_config()
                    self.stdout.write(f'   Username: {admin_config["username"]}  Password: {admin_config["password"]}')
                    if test_config['create_test_users']:
                        self.stdout.write(f'   Test users: manager1  Password: {test_config["test_password"]}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Initialization failed: {str(e)}'))
                raise

    def create_team_roles(self):
        """Create essential team roles"""
        self.stdout.write('🎭 Creating team roles...')
        
        roles_data = [
            ('member', 'Team Member', 'Standard team member'),
            ('coordinator', 'Team Coordinator', 'Coordinates team activities'),
            ('lead', 'Team Lead', 'Team leadership and management'),
            ('scheduler', 'Team Scheduler', 'Schedule planning and coordination'),
        ]
        
        roles_created = 0
        for name, display_name, description in roles_data:
            role, created = TeamRole.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'can_assign_shifts': name in ['lead', 'scheduler'],
                    'can_approve_swaps': name in ['lead', 'coordinator'],
                    'can_manage_team': name == 'lead',
                }
            )
            if created:
                roles_created += 1
                self.stdout.write(f'  + Created role: {name}')
        
        self.stdout.write(f'  ✅ Created {roles_created} team roles')

    def create_teams(self):
        """Create essential teams"""
        self.stdout.write('👥 Creating teams...')
        
        teams_data = [
            ('TPS Alpha Team', 'Primary response team', 'Operations'),
            ('TPS Beta Team', 'Secondary support team', 'Support'),
            ('TPS Gamma Team', 'Specialized operations team', 'Projects'),
        ]
        
        teams_created = 0
        for name, description, department in teams_data:
            team, created = Team.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'department': department,
                    'is_active': True,
                }
            )
            if created:
                teams_created += 1
                self.stdout.write(f'  + Created team: {name}')
        
        self.stdout.write(f'  ✅ Created {teams_created} teams')

    def create_skill_system(self):
        """Create skill categories and skills"""
        self.stdout.write('🎯 Creating skill system...')
        
        # Skill categories
        categories_data = [
            ('Technical', 'Technical skills', '#3B82F6'),
            ('Security', 'Security expertise', '#EF4444'),
            ('Infrastructure', 'Infrastructure management', '#10B981'),
            ('Communication', 'Communication skills', '#F59E0B'),
            ('Waakdienst', 'Waakdienst and on-call duties', '#9333EA'),
            ('Incident', 'Incident response and emergency handling', '#DC2626'),
        ]
        
        cat_created = 0
        for name, description, color in categories_data:
            category, created = SkillCategory.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'color': color,
                }
            )
            if created:
                cat_created += 1
        
        # Essential skills - including orchestrator requirements
        skills_data = [
            # Core orchestrator skills (exact names required)
            ('Waakdienst', 'Waakdienst', 'intermediate'),
            ('Incidenten', 'Incident', 'intermediate'),
            # Traditional technical skills
            ('Linux Administration', 'Technical', 'intermediate'),
            ('Network Troubleshooting', 'Technical', 'basic'),
            ('Security Incident Response', 'Security', 'intermediate'),
            ('Database Management', 'Technical', 'intermediate'),
            ('Cloud Platforms', 'Infrastructure', 'basic'),
            ('Monitoring Systems', 'Infrastructure', 'basic'),
            ('Customer Communication', 'Communication', 'basic'),
            ('Documentation', 'Communication', 'basic'),
            ('Problem Solving', 'Technical', 'basic'),
            ('Team Coordination', 'Communication', 'intermediate'),
        ]
        
        skills_created = 0
        for skill_name, category_name, min_level in skills_data:
            category = SkillCategory.objects.get(name=category_name)
            skill, created = Skill.objects.get_or_create(
                name=skill_name,
                defaults={
                    'category': category,
                    'minimum_level_required': min_level,
                    'requires_certification': False,
                }
            )
            if created:
                skills_created += 1
        
        self.stdout.write(f'  ✅ Created {cat_created} categories and {skills_created} skills')
    
    def create_shift_system(self):
        """Create shift categories and templates"""
        self.stdout.write('⏰ Creating shift system...')
        
        # Shift categories with all required parameters
        categories_data = [
            ('WAAKDIENST', 'Waakdienst', 'On-call duty shifts', '#EF4444', 12, 40, 7, True, False),
            ('INCIDENT', 'Incident Response', 'Emergency incident handling', '#F59E0B', 26, 16, 1, False, True),
            ('SUPPORT', 'Business Support', 'Standard business support', '#10B981', 52, 40, 0, False, True),
            ('MAINTENANCE', 'System Maintenance', 'Planned maintenance windows', '#06B6D4', 26, 24, 3, False, True),
        ]
        
        cat_created = 0
        for name, display_name, description, color, max_weeks, hours_per_week, min_gap_days, requires_handover, allows_auto_assignment in categories_data:
            category, created = ShiftCategory.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'color': color,
                    'max_weeks_per_year': max_weeks,
                    'hours_per_week': hours_per_week,
                    'min_gap_days': min_gap_days,
                    'requires_handover': requires_handover,
                    'allows_auto_assignment': allows_auto_assignment,
                }
            )
            if created:
                cat_created += 1
        
        # Shift templates
        templates_data = [
            ('Weekend Waakdienst', 'WAAKDIENST', '09:00', '17:00', 8, False, True),
            ('Evening Waakdienst', 'WAAKDIENST', '17:00', '09:00', 16, True, False),
            ('Incident Response', 'INCIDENT', '08:00', '16:00', 8, False, False),
            ('Business Support', 'SUPPORT', '09:00', '17:00', 8, False, False),
            ('Maintenance Window', 'MAINTENANCE', '02:00', '06:00', 4, True, False),
        ]
        
        temp_created = 0
        for name, category_name, start_time, end_time, duration, is_overnight, is_weekly in templates_data:
            category = ShiftCategory.objects.get(name=category_name)
            template, created = ShiftTemplate.objects.get_or_create(
                name=name,
                category=category,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_hours': duration,
                    'is_overnight': is_overnight,
                    'is_weekly_shift': is_weekly,
                    'spans_weekend': False,
                    'days_of_week': [1, 2, 3, 4, 5] if not is_weekly else [1, 2, 3, 4, 5, 6, 7],
                    'engineers_required': 1,
                    'backup_engineers': 0,
                }
            )
            if created:
                temp_created += 1
        
        self.stdout.write(f'  ✅ Created {cat_created} shift categories and {temp_created} templates')

    def create_users(self, production=False):
        """Create user accounts"""
        self.stdout.write('👤 Creating user accounts...')
        
        # Get configuration
        admin_config = config_manager.get_admin_config()
        test_config = config_manager.get_test_config()
        org_config = config_manager.get_organization_config()
        
        users_created = 0
        
        # Create or update admin user
        admin_username = admin_config['username']
        admin_user = User.objects.filter(username=admin_username).first()
        if not admin_user:
            admin = User.objects.create_superuser(
                username=admin_config['username'],
                email=admin_config['email'],
                password=admin_config['password'],
                first_name=admin_config['first_name'],
                last_name=admin_config['last_name']
            )
            admin.employee_id = config_manager.generate_employee_id(1, 'ADM')
            admin.role = 'ADMIN'
            admin.phone = config_manager.generate_phone_number()
            admin.save()
            users_created += 1
            self.stdout.write('  + Created admin user')
        else:
            # Update existing admin user
            if not admin_user.employee_id:
                admin_user.employee_id = config_manager.generate_employee_id(1, 'ADM')
            if not hasattr(admin_user, 'role') or not admin_user.role:
                admin_user.role = 'ADMIN'
            if not admin_user.phone:
                admin_user.phone = config_manager.generate_phone_number()
            admin_user.save()
            self.stdout.write('  + Updated existing admin user')
        
        if production:
            # Minimal production users
            production_users = [
                ('planner', 'Planning', 'User', 'PLANNER', config_manager.generate_employee_id(1, 'PLN')),
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
                    users_created += 1
                    self.stdout.write(f'  + Created {role.lower()} user: {username} (password: {secure_password})')
        else:
            # Test users if enabled
            if test_config['create_test_users']:
                test_users_data = [
                    ('planner1', 'Alice', 'Planner', 'PLANNER', config_manager.generate_employee_id(1, 'PLN')),
                    ('manager1', 'Bob', 'Manager', 'MANAGER', config_manager.generate_employee_id(1, 'MGR')),
                    ('user1', 'Charlie', 'Engineer', 'USER', config_manager.generate_employee_id(1)),
                    ('user2', 'Diana', 'Technician', 'USER', config_manager.generate_employee_id(2)),
                    ('user3', 'Edward', 'Analyst', 'USER', config_manager.generate_employee_id(3)),
                    ('user4', 'Fiona', 'Specialist', 'USER', config_manager.generate_employee_id(4)),
                    ('user5', 'George', 'Coordinator', 'USER', config_manager.generate_employee_id(5)),
                ]
                
                for username, first_name, last_name, role, emp_id in test_users_data:
                    if not User.objects.filter(username=username).exists() and not User.objects.filter(employee_id=emp_id).exists():
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
                        users_created += 1
                        self.stdout.write(f'  + Created test user: {username} ({role})')
                        
                        # Assign to a team
                        if role == 'USER':
                            teams = list(Team.objects.all())
                            if teams:
                                team = random.choice(teams)
                                member_role = TeamRole.objects.get(name='member')
                                TeamMembership.objects.get_or_create(
                                    user=user,
                                    team=team,
                                    defaults={'role': member_role}
                                )
                    else:
                        if User.objects.filter(username=username).exists():
                            self.stdout.write(f'  ! Skipped {username} - username already exists')
                        elif User.objects.filter(employee_id=emp_id).exists():
                            self.stdout.write(f'  ! Skipped {username} - employee_id {emp_id} already exists')
        
        self.stdout.write(f'  ✅ Created {users_created} user accounts')
        
        # Assign some skills to test users
        if not production and test_config['create_test_users']:
            self.assign_skills_to_users()

    def assign_skills_to_users(self):
        """Assign random skills to users for testing"""
        self.stdout.write('🎯 Assigning skills to users...')
        
        skills = list(Skill.objects.all())
        users = User.objects.filter(role='USER')
        
        # Get the orchestrator-required skills
        waakdienst_skill = Skill.objects.filter(name='Waakdienst').first()
        incident_skill = Skill.objects.filter(name='Incidenten').first()
        
        assignments = 0
        for user in users:
            # Ensure each user gets either Waakdienst or Incident skill (or both)
            required_skills = []
            if waakdienst_skill and incident_skill:
                # Randomly assign waakdienst and/or incident skills
                if random.choice([True, False]):  # 50% get waakdienst
                    required_skills.append(waakdienst_skill)
                if random.choice([True, False]):  # 50% get incident
                    required_skills.append(incident_skill)
                
                # Ensure each user has at least one of the core skills
                if not required_skills:
                    required_skills.append(random.choice([waakdienst_skill, incident_skill]))
            
            # Assign the required skills first
            for skill in required_skills:
                proficiency_levels = ['intermediate', 'advanced']  # Higher proficiency for core skills
                proficiency = random.choice(proficiency_levels)
                
                user_skill, created = UserSkill.objects.get_or_create(
                    user=user,
                    skill=skill,
                    defaults={
                        'proficiency_level': proficiency,
                        'is_certified': False,
                    }
                )
                
                if created:
                    assignments += 1
            
            # Assign 1-3 additional random skills per user
            num_additional_skills = random.randint(1, 3)
            available_skills = [s for s in skills if s not in required_skills]
            if available_skills:
                additional_skills = random.sample(available_skills, min(num_additional_skills, len(available_skills)))
                
                for skill in additional_skills:
                    proficiency_levels = ['basic', 'intermediate', 'advanced']
                    proficiency = random.choice(proficiency_levels)
                    
                    user_skill, created = UserSkill.objects.get_or_create(
                        user=user,
                        skill=skill,
                        defaults={
                            'proficiency_level': proficiency,
                            'is_certified': False,
                        }
                    )
                    
                    if created:
                        assignments += 1
        
        self.stdout.write(f'  ✅ Created {assignments} skill assignments')
