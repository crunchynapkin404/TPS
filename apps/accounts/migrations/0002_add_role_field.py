"""
Migration to add role field to User model
"""

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('USER', 'User'),
                    ('PLANNER', 'Planner'), 
                    ('MANAGER', 'Manager')
                ],
                default='USER',
                help_text="User's role in the TPS system",
                max_length=10
            ),
        ),
    ]
