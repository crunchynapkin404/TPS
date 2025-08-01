from django.core.management.base import BaseCommand
from apps.accounts.models import SkillCategory, Skill
from apps.teams.models import TeamRole


class Command(BaseCommand):
    help = 'Create initial skills and team roles for TPS registration'

    def handle(self, *args, **options):
        # Create Skill Categories
        skill_category, created = SkillCategory.objects.get_or_create(
            name='Operations',
            defaults={
                'description': 'Operational skills for TPS system',
                'color': '#3B82F6'
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created skill category: {skill_category.name}')
            )

        # Create Skills required for registration
        skills_to_create = [
            {
                'name': 'Waakdienst',
                'description': 'On-call duty and monitoring responsibilities'
            },
            {
                'name': 'Incident',
                'description': 'Incident response and management'
            }
        ]

        for skill_data in skills_to_create:
            skill, created = Skill.objects.get_or_create(
                name=skill_data['name'],
                category=skill_category,
                defaults={
                    'description': skill_data['description'],
                    'minimum_level_required': 'basic',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created skill: {skill.name}')
                )

        # Create Team Roles required for registration
        team_roles_to_create = [
            ('member', 'Team Member'),
            ('coordinator', 'Team Coordinator'),
            ('lead', 'Team Lead'),
            ('deputy_lead', 'Deputy Team Lead'),
            ('trainer', 'Team Trainer'),
            ('scheduler', 'Team Scheduler'),
            ('operationeel', 'Operationeel'),
            ('tactisch', 'Tactisch'),
        ]

        for role_name, role_display in team_roles_to_create:
            role, created = TeamRole.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': f'{role_display} role in team operations'
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created team role: {role.get_name_display()}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully created initial data for registration!')
        )