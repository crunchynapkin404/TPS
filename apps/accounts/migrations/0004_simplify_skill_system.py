"""
Migration to simplify the skill system to only 4 basic skills:
- Incidenten (Incident Response)
- Projects (Project Work) 
- Changes (Change Management)
- Waakdienst (On-call Duty)
"""

from django.db import migrations


def create_simplified_skills(apps, schema_editor):
    """Create the simplified skill system"""
    SkillCategory = apps.get_model('accounts', 'SkillCategory')
    Skill = apps.get_model('accounts', 'Skill')
    
    # Delete all existing skills and categories
    Skill.objects.all().delete()
    SkillCategory.objects.all().delete()
    
    # Create single Operations category
    operations_category = SkillCategory.objects.create(
        name='Operations',
        description='Core operational skills for TPS system',
        color='#3B82F6',
        is_active=True
    )
    
    # Create the 4 basic skills
    skills_data = [
        ('Incidenten', 'Incident response and handling', 'basic', False, None),
        ('Projects', 'Project work and development (daily default work)', 'basic', False, None),
        ('Changes', 'Change management and implementation (daily default work)', 'basic', False, None),
        ('Waakdienst', 'On-call duty and emergency response', 'intermediate', True, 12),
    ]
    
    for skill_name, description, min_level, requires_cert, cert_months in skills_data:
        Skill.objects.create(
            name=skill_name,
            category=operations_category,
            description=description,
            minimum_level_required=min_level,
            requires_certification=requires_cert,
            certification_validity_months=cert_months,
            is_active=True
        )


def reverse_simplify_skills(apps, schema_editor):
    """Reverse the simplification - just delete all skills"""
    SkillCategory = apps.get_model('accounts', 'SkillCategory')
    Skill = apps.get_model('accounts', 'Skill')
    
    Skill.objects.all().delete()
    SkillCategory.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_add_admin_role'),
    ]

    operations = [
        migrations.RunPython(create_simplified_skills, reverse_simplify_skills),
    ]