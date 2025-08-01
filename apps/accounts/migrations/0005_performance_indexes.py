# Generated performance optimization migration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_simplify_skill_system'),
        ('teams', '0002_alter_teamrole_name'),
        ('assignments', '0001_initial'),
        ('scheduling', '0001_initial'),
        ('leave_management', '0001_initial'),
    ]

    operations = [
        # Add database indexes for performance optimization
        
        # User model indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_role ON tps_users (role);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_role;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_active_employee ON tps_users (is_active_employee);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_active_employee;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_ytd_stats ON tps_users (ytd_waakdienst_weeks, ytd_incident_weeks);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_ytd_stats;"
        ),
        
        # Assignment model indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_assignment_status ON tps_assignments (status);",
            reverse_sql="DROP INDEX IF EXISTS idx_assignment_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_assignment_assigned_at ON tps_assignments (assigned_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_assignment_assigned_at;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_assignment_user_status ON tps_assignments (user_id, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_assignment_user_status;"
        ),
        
        # Team membership indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_team_membership_active ON tps_team_memberships (is_active, user_id, team_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_team_membership_active;"
        ),
        
        # Leave request indexes  
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_leave_request_status ON tps_leave_requests (status);",
            reverse_sql="DROP INDEX IF EXISTS idx_leave_request_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_leave_request_dates ON tps_leave_requests (start_date, end_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_leave_request_dates;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_leave_request_user_status ON tps_leave_requests (user_id, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_leave_request_user_status;"
        ),
        
        # Shift instance indexes for scheduling queries
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_shift_instance_datetime ON tps_shift_instances (start_datetime, end_datetime);",
            reverse_sql="DROP INDEX IF EXISTS idx_shift_instance_datetime;"
        ),
        
        # User skills indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_skill_proficiency ON tps_user_skills (user_id, proficiency_level);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_skill_proficiency;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_skill_certified ON tps_user_skills (is_certified, certification_expiry);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_skill_certified;"
        ),
        
        # Leave balance indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_leave_balance_user_year ON tps_leave_balances (user_id, year);",
            reverse_sql="DROP INDEX IF EXISTS idx_leave_balance_user_year;"
        ),
    ]