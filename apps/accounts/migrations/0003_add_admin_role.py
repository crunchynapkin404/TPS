"""
Migration to add ADMIN role to User model choices
"""

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_add_role_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('USER', 'User'),
                    ('PLANNER', 'Planner'), 
                    ('MANAGER', 'Manager'),
                    ('ADMIN', 'Administrator')
                ],
                default='USER',
                help_text="User's role in the TPS system",
                max_length=10
            ),
        ),
    ]
