"""
Management command to easily assign skills to users
Supports the simplified 4-skill system for TPS
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.accounts.models import Skill, UserSkill
from apps.teams.models import TeamMembership

User = get_user_model()


class Command(BaseCommand):
    help = 'Easily manage user skills in the simplified TPS system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--assign',
            action='store_true',
            help='Assign skills to users interactively'
        )
        parser.add_argument(
            '--bulk-assign',
            action='store_true',
            help='Bulk assign skills based on team roles'
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='List all users and their current skills'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username or employee ID for single user operations'
        )
        parser.add_argument(
            '--skills',
            type=str,
            help='Comma-separated list of skills to assign (Incidenten,Projects,Changes,Waakdienst)'
        )
        parser.add_argument(
            '--proficiency',
            type=str,
            default='basic',
            choices=['learning', 'basic', 'intermediate', 'advanced', 'expert'],
            help='Proficiency level for assigned skills'
        )
    
    def handle(self, *args, **options):
        if options['list_users']:
            self.list_users_and_skills()
        elif options['assign']:
            self.interactive_skill_assignment()
        elif options['bulk_assign']:
            self.bulk_assign_skills()
        elif options['user'] and options['skills']:
            self.assign_skills_to_user(options['user'], options['skills'], options['proficiency'])
        else:
            self.show_help()
    
    def show_help(self):
        """Show usage examples"""
        self.stdout.write(self.style.SUCCESS('TPS Skill Management Commands:'))
        self.stdout.write('')
        self.stdout.write('List all users and their skills:')
        self.stdout.write('  python manage.py manage_user_skills --list-users')
        self.stdout.write('')
        self.stdout.write('Assign skills to a specific user:')
        self.stdout.write('  python manage.py manage_user_skills --user user1 --skills "Incidenten,Projects,Changes"')
        self.stdout.write('')
        self.stdout.write('Interactive skill assignment:')
        self.stdout.write('  python manage.py manage_user_skills --assign')
        self.stdout.write('')
        self.stdout.write('Bulk assign based on team structure:')
        self.stdout.write('  python manage.py manage_user_skills --bulk-assign')
        self.stdout.write('')
        self.stdout.write('Available skills: Incidenten, Projects, Changes, Waakdienst')
    
    def list_users_and_skills(self):
        """List all users and their current skills"""
        self.stdout.write(self.style.SUCCESS('Current User Skills:'))
        self.stdout.write('=' * 60)
        
        users = User.objects.filter(is_active=True).order_by('last_name')
        for user in users:
            user_skills = UserSkill.objects.filter(user=user).select_related('skill')
            skills_list = [f"{us.skill.name}({us.proficiency_level})" for us in user_skills]
            
            # Get team info
            team_membership = TeamMembership.objects.filter(user=user, is_active=True).first()
            team_info = f" - {team_membership.team.name}" if team_membership else ""
            
            self.stdout.write(
                f"{user.get_full_name()} ({user.username}){team_info}: "
                f"{', '.join(skills_list) if skills_list else 'No skills assigned'}"
            )
    
    def interactive_skill_assignment(self):
        """Interactive skill assignment"""
        self.stdout.write(self.style.SUCCESS('Interactive Skill Assignment'))
        self.stdout.write('=' * 40)
        
        # Show available users
        users = User.objects.filter(is_active=True).exclude(username='admin').order_by('last_name')
        self.stdout.write('\nAvailable users:')
        for i, user in enumerate(users, 1):
            team_info = ""
            team_membership = TeamMembership.objects.filter(user=user, is_active=True).first()
            if team_membership:
                team_info = f" ({team_membership.team.name})"
            self.stdout.write(f"  {i}. {user.get_full_name()} ({user.username}){team_info}")
        
        # Get user selection
        try:
            user_choice = int(input('\nSelect user number: ')) - 1
            selected_user = users[user_choice]
        except (ValueError, IndexError):
            self.stdout.write(self.style.ERROR('Invalid user selection'))
            return
        
        # Show available skills
        skills = Skill.objects.filter(is_active=True).order_by('name')
        self.stdout.write(f'\nAssigning skills to: {selected_user.get_full_name()}')
        self.stdout.write('\nAvailable skills:')
        for i, skill in enumerate(skills, 1):
            self.stdout.write(f"  {i}. {skill.name} - {skill.description}")
        
        # Get skill selections
        skill_input = input('\nEnter skill numbers (comma-separated) or skill names: ')
        
        # Parse skill selections
        selected_skills = []
        if skill_input.strip():
            for item in skill_input.split(','):
                item = item.strip()
                if item.isdigit():
                    # User entered a number
                    try:
                        skill_index = int(item) - 1
                        selected_skills.append(skills[skill_index])
                    except IndexError:
                        self.stdout.write(self.style.WARNING(f'Invalid skill number: {item}'))
                else:
                    # User entered a skill name
                    skill = skills.filter(name__icontains=item).first()
                    if skill:
                        selected_skills.append(skill)
                    else:
                        self.stdout.write(self.style.WARNING(f'Skill not found: {item}'))
        
        if not selected_skills:
            self.stdout.write(self.style.ERROR('No valid skills selected'))
            return
        
        # Get proficiency level
        proficiency = input('\nProficiency level (learning/basic/intermediate/advanced/expert) [basic]: ').strip() or 'basic'
        if proficiency not in ['learning', 'basic', 'intermediate', 'advanced', 'expert']:
            proficiency = 'basic'
        
        # Assign skills
        self.assign_skills_to_user_obj(selected_user, selected_skills, proficiency)
    
    def assign_skills_to_user(self, user_identifier, skills_str, proficiency):
        """Assign skills to a specific user"""
        # Find user
        try:
            if '@' in user_identifier:
                user = User.objects.get(email=user_identifier)
            elif user_identifier.startswith('EMP') or user_identifier.startswith('ADM'):
                user = User.objects.get(employee_id=user_identifier)
            else:
                user = User.objects.get(username=user_identifier)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {user_identifier}'))
            return
        
        # Parse skills
        skill_names = [s.strip() for s in skills_str.split(',')]
        skills = []
        for skill_name in skill_names:
            try:
                skill = Skill.objects.get(name__icontains=skill_name, is_active=True)
                skills.append(skill)
            except Skill.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Skill not found: {skill_name}'))
        
        if not skills:
            self.stdout.write(self.style.ERROR('No valid skills provided'))
            return
        
        self.assign_skills_to_user_obj(user, skills, proficiency)
    
    def assign_skills_to_user_obj(self, user, skills, proficiency):
        """Assign skills to a user object"""
        with transaction.atomic():
            assigned_count = 0
            updated_count = 0
            
            for skill in skills:
                user_skill, created = UserSkill.objects.get_or_create(
                    user=user,
                    skill=skill,
                    defaults={
                        'proficiency_level': proficiency,
                        'is_certified': False
                    }
                )
                
                if created:
                    assigned_count += 1
                    self.stdout.write(f'  + Assigned {skill.name} to {user.get_full_name()}')
                else:
                    # Update existing skill
                    user_skill.proficiency_level = proficiency
                    user_skill.save()
                    updated_count += 1
                    self.stdout.write(f'  * Updated {skill.name} for {user.get_full_name()} to {proficiency}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Skills management complete: {assigned_count} assigned, {updated_count} updated'
                )
            )
    
    def bulk_assign_skills(self):
        """Bulk assign skills based on team structure requirements"""
        self.stdout.write(self.style.SUCCESS('Bulk Skill Assignment'))
        self.stdout.write('This will assign basic skills to users based on the team structure requirements.')
        
        confirmation = input('Continue? (y/N): ')
        if confirmation.lower() != 'y':
            self.stdout.write('Cancelled')
            return
        
        # Get all skills
        try:
            incidenten = Skill.objects.get(name='Incidenten')
            projects = Skill.objects.get(name='Projects')
            changes = Skill.objects.get(name='Changes') 
            waakdienst = Skill.objects.get(name='Waakdienst')
        except Skill.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Required skill not found: {e}'))
            return
        
        # Assign skills to all active users (basic operational skills)
        users = User.objects.filter(is_active=True).exclude(username='admin')
        
        with transaction.atomic():
            for user in users:
                # All users get Projects and Changes (daily default work)
                for skill in [projects, changes]:
                    UserSkill.objects.get_or_create(
                        user=user,
                        skill=skill,
                        defaults={'proficiency_level': 'basic', 'is_certified': False}
                    )
                
                # Check team membership to determine additional skills
                team_membership = TeamMembership.objects.filter(user=user, is_active=True).first()
                
                if team_membership:
                    team_name = team_membership.team.name.lower()
                    role_name = team_membership.role.name.lower() if team_membership.role else 'member'
                    
                    # Assign Incidenten to most users (operational teams)
                    if 'infrastructure' in team_name or 'operations' in team_name or 'incident' in team_name:
                        UserSkill.objects.get_or_create(
                            user=user,
                            skill=incidenten,
                            defaults={'proficiency_level': 'basic', 'is_certified': False}
                        )
                    
                    # Assign Waakdienst to planners and team leads
                    if 'lead' in role_name or 'planner' in role_name or 'coordinator' in role_name:
                        UserSkill.objects.get_or_create(
                            user=user,
                            skill=waakdienst,
                            defaults={'proficiency_level': 'intermediate', 'is_certified': False}
                        )
                    
                    self.stdout.write(f'Assigned skills to {user.get_full_name()} ({team_name} - {role_name})')
                else:
                    # Users without teams get basic operational skills
                    UserSkill.objects.get_or_create(
                        user=user,
                        skill=incidenten,
                        defaults={'proficiency_level': 'basic', 'is_certified': False}
                    )
                    self.stdout.write(f'Assigned basic skills to {user.get_full_name()} (no team)')
        
        self.stdout.write(self.style.SUCCESS('Bulk skill assignment completed'))
        self.stdout.write('\nRun --list-users to see the results')