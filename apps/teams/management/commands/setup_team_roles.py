from django.core.management.base import BaseCommand
from apps.teams.models import TeamRole


class Command(BaseCommand):
    help = 'Set up required team roles for TPS registration system'

    def handle(self, *args, **options):
        # Team roles required for registration
        required_roles = [
            ('operationeel', 'Operationeel'),
            ('tactisch', 'Tactisch'),
            ('member', 'Team Member'),
            ('coordinator', 'Team Coordinator'),
            ('lead', 'Team Lead'),
            ('deputy_lead', 'Deputy Team Lead'),
            ('trainer', 'Team Trainer'),
            ('scheduler', 'Team Scheduler'),
        ]

        created_count = 0
        
        for role_name, display_name in required_roles:
            role, created = TeamRole.objects.get_or_create(
                name=role_name,
                defaults={'description': f'{display_name} - Team position'}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created team role: {role_name} ({display_name})')
                )
                created_count += 1
            else:
                self.stdout.write(f'Team role already exists: {role_name}')

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} team roles')
            )
        else:
            self.stdout.write('All required team roles already exist')

        # Display current team roles
        self.stdout.write('\nCurrent team roles in database:')
        for role in TeamRole.objects.all().order_by('name'):
            self.stdout.write(f'  - {role.name}: {role.get_name_display()}')
