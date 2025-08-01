"""
Management command to create test data for TPS calendar testing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.teams.models import Team, TeamRole, TeamMembership
from apps.accounts.models import SkillCategory, Skill, UserSkill
from apps.scheduling.models import ShiftCategory, ShiftTemplate, ShiftInstance, PlanningPeriod
from core.config import config_manager
from datetime import date, datetime, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for TPS calendar functionality testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of test users to create'
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=4,
            help='Number of weeks of shift data to create'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Creating test data for TPS calendar...')
        
        # Get configuration
        admin_config = config_manager.get_admin_config()
        test_config = config_manager.get_test_config()
        org_config = config_manager.get_organization_config()
        
        # Create skill categories and skills
        self.create_skills()
        
        # Create shift categories and templates
        self.create_shift_templates()
        
        # Create teams and roles
        teams = self.create_teams()
        
        # Create users
        users = self.create_users(options['users'], admin_config, test_config, org_config)
        
        # Assign users to teams
        self.assign_users_to_teams(users, teams)
        
        # Create planning period and shifts
        self.create_planning_period_and_shifts(options['weeks'])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test data:\n'
                f'- {len(users)} users\n'
                f'- {len(teams)} teams\n'
                f'- {options["weeks"]} weeks of shift data\n'
                f'- Admin user: {admin_config["username"]}/[password from config]\n'
                f'- Test users: user1/[test password], user2/[test password], etc.'
            )
        )
    
    def create_skills(self):
        """Create skill categories and skills"""
        self.stdout.write('Creating skills...')
        
        # Create skill categories
        technical = SkillCategory.objects.get_or_create(
            name='Operations',
            defaults={'description': 'Operational skills for TPS', 'color': '#3B82F6'}
        )[0]
        
        # Create only 2 simple skills
        skills_data = [
            ('Waakdienst', technical, 'basic'),
            ('Incidenten', technical, 'basic'),
        ]
        
        for skill_name, category, min_level in skills_data:
            Skill.objects.get_or_create(
                name=skill_name,
                defaults={
                    'category': category,
                    'minimum_level_required': min_level,
                    'requires_certification': random.choice([True, False])
                }
            )
    
    def create_shift_templates(self):
        """Create shift categories and templates"""
        self.stdout.write('Creating shift templates...')
        
        # Create shift categories
        categories_data = [
            ('WAAKDIENST', 'Waakdienst', '#EF4444', 12, 40, 7),
            ('INCIDENT', 'Incident Response', '#F59E0B', 52, 8, 1),
            ('CHANGES', 'Change Management', '#8B5CF6', 26, 16, 3),
            ('PROJECTS', 'Project Work', '#10B981', 52, 40, 1),
        ]
        
        for name, display_name, color, max_weeks, hours_per_week, min_gap in categories_data:
            ShiftCategory.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'color': color,
                    'max_weeks_per_year': max_weeks,
                    'hours_per_week': hours_per_week,
                    'min_gap_days': min_gap
                }
            )
        
        # Create shift templates
        waakdienst = ShiftCategory.objects.get(name='WAAKDIENST')
        incident = ShiftCategory.objects.get(name='INCIDENT')
        
        templates_data = [
            ('Weekend Waakdienst', waakdienst, '09:00', '17:00', 8, True, True),
            ('Evening Waakdienst', waakdienst, '17:00', '09:00', 16, False, True),
            ('Incident Response', incident, '08:00', '17:00', 9, False, False),
            ('Night Support', incident, '22:00', '06:00', 8, False, True),
        ]
        
        for name, category, start_time, end_time, duration, weekly, overnight in templates_data:
            ShiftTemplate.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_hours': duration,
                    'is_weekly_shift': weekly,
                    'is_overnight': overnight,
                    'engineers_required': 1,
                    'backup_engineers': 0,
                    'is_active': True
                }
            )
    
    def create_teams(self):
        """Create teams and roles"""
        self.stdout.write('Creating teams...')
        
        # Create global team roles first
        roles_data = [
            ('member', 'Team Member', False, False, False),
            ('coordinator', 'Team Coordinator', True, False, False),
            ('lead', 'Team Lead', True, True, True),
            ('deputy_lead', 'Deputy Team Lead', True, True, False),
            ('trainer', 'Team Trainer', False, False, False),
            ('scheduler', 'Team Scheduler', True, False, False),
        ]
        
        for name, description, can_assign, can_approve, can_manage in roles_data:
            TeamRole.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'can_assign_shifts': can_assign,
                    'can_approve_swaps': can_approve,
                    'can_manage_team': can_manage
                }
            )
        
        teams_data = [
            ('Infrastructure Team', 'IT', 'Manages servers and infrastructure'),
            ('Application Support', 'AS', 'Supports business applications'),
            ('Network Operations', 'NO', 'Network monitoring and management'),
        ]
        
        teams = []
        for name, department, description in teams_data:
            team = Team.objects.get_or_create(
                name=name,
                defaults={
                    'department': department,
                    'description': description,
                    'is_active': True
                }
            )[0]
            teams.append(team)
        
        return teams
    
    def create_users(self, num_users, admin_config, test_config, org_config):
        """Create test users using configuration"""
        self.stdout.write(f'Creating {num_users} test users...')
        
        # Create superuser if not exists
        admin_username = admin_config['username']
        if not User.objects.filter(username=admin_username).exists():
            admin = User.objects.create_superuser(
                username=admin_config['username'],
                email=admin_config['email'],
                password=admin_config['password'],
                first_name=admin_config['first_name'],
                last_name=admin_config['last_name']
            )
            admin.employee_id = config_manager.generate_employee_id(1, 'ADM')
            admin.save()
        
        users = []
        if test_config['create_test_users']:
            for i in range(1, num_users + 1):
                username = f'user{i}'
                employee_id = config_manager.generate_employee_id(i)
                
                if not User.objects.filter(username=username).exists() and not User.objects.filter(employee_id=employee_id).exists():
                    user = User.objects.create_user(
                        username=username,
                        email=config_manager.generate_test_email(username),
                        password=test_config['test_password'],
                        first_name=f'User',
                        last_name=f'{i:02d}'
                    )
                    user.employee_id = employee_id
                    user.phone = config_manager.generate_phone_number()
                    user.emergency_contact = f'Emergency Contact {i}'
                    user.emergency_phone = config_manager.generate_phone_number()
                    user.save()
                    users.append(user)
                    
                    # Assign skills - simplified system
                    skills = list(Skill.objects.all())
                    # Give each user 1-2 skills randomly
                    num_skills = random.randint(1, 2)
                    for skill in random.sample(skills, min(num_skills, len(skills))):
                        UserSkill.objects.get_or_create(
                            user=user,
                            skill=skill,
                            defaults={
                                'proficiency_level': 'basic',  # All basic level
                                'is_certified': random.choice([True, False]),
                                'certification_date': timezone.now() if random.choice([True, False]) else None
                            }
                        )
        
        return users
    
    def assign_users_to_teams(self, users, teams):
        """Assign users to teams with roles"""
        self.stdout.write('Assigning users to teams...')
        
        # Get available roles
        lead_role = TeamRole.objects.get(name='lead')
        coordinator_role = TeamRole.objects.get(name='coordinator')
        member_role = TeamRole.objects.get(name='member')
        
        for i, user in enumerate(users):
            # Assign each user to a random team
            team = teams[i % len(teams)]  # Distribute evenly across teams
            
            # Assign role - first user gets lead, second gets coordinator, rest are members
            if i == 0:
                role = lead_role
            elif i == 1:
                role = coordinator_role
            else:
                role = member_role
            
            TeamMembership.objects.get_or_create(
                user=user,
                team=team,
                defaults={
                    'role': role,
                    'join_date': date.today(),
                    'is_active': True
                }
            )
    
    def create_planning_period_and_shifts(self, weeks):
        """Create planning period and shift instances"""
        self.stdout.write(f'Creating {weeks} weeks of shift data...')
        
        # Create planning period
        start_date = date.today()
        end_date = start_date + timedelta(weeks=weeks)
        
        period = PlanningPeriod.objects.get_or_create(
            name=f'Test Period {start_date.strftime("%Y-%m")}',
            defaults={
                'period_type': 'custom',
                'start_date': start_date,
                'end_date': end_date,
                'planning_deadline': timezone.now() + timedelta(days=7),
                'status': 'published',
                'allows_auto_generation': True
            }
        )[0]
        
        # Create shift instances
        templates = ShiftTemplate.objects.filter(is_active=True)
        current_date = start_date
        
        while current_date <= end_date:
            # Create weekend waakdienst shifts
            if current_date.weekday() >= 5:  # Saturday or Sunday
                weekend_template = templates.filter(name='Weekend Waakdienst').first()
                if weekend_template:
                    start_datetime = timezone.make_aware(datetime.combine(current_date, weekend_template.start_time))
                    end_datetime = timezone.make_aware(datetime.combine(current_date, weekend_template.end_time))
                    
                    ShiftInstance.objects.get_or_create(
                        template=weekend_template,
                        date=current_date,
                        defaults={
                            'start_datetime': start_datetime,
                            'end_datetime': end_datetime,
                            'status': 'published',
                            'planning_period': period
                        }
                    )
            
            # Create incident response shifts on weekdays
            if current_date.weekday() < 5:  # Monday to Friday
                incident_template = templates.filter(name='Incident Response').first()
                if incident_template:
                    start_datetime = timezone.make_aware(datetime.combine(current_date, incident_template.start_time))
                    end_datetime = timezone.make_aware(datetime.combine(current_date, incident_template.end_time))
                    
                    ShiftInstance.objects.get_or_create(
                        template=incident_template,
                        date=current_date,
                        defaults={
                            'start_datetime': start_datetime,
                            'end_datetime': end_datetime,
                            'status': 'published',
                            'planning_period': period
                        }
                    )
            
            current_date += timedelta(days=1)
