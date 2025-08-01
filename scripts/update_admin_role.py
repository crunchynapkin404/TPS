import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tps_project.settings')
django.setup()

from apps.accounts.models import User

# Update admin user to have ADMIN role
admin_user = User.objects.filter(is_superuser=True).first()
if admin_user:
    admin_user.role = 'ADMIN'
    admin_user.save()
    print(f"Updated {admin_user.username} to ADMIN role")
else:
    print("No superuser found")

# Check current user roles
print("\nCurrent users and their roles:")
for user in User.objects.all()[:10]:  # First 10 users
    print(f"- {user.username}: {user.role} ({user.get_role_display()})")
