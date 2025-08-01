"""
TPS Configuration Utilities
Provides secure configuration management and data generation utilities
"""

import os
import secrets
import string
from django.core.management.utils import get_random_secret_key
from faker import Faker


class ConfigManager:
    """Manages configuration settings and secure data generation"""
    
    def __init__(self):
        self.fake = Faker()
        
        # Configuration from environment
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.test_domain = os.getenv('TEST_DOMAIN', 'tps.local')
        self.org_domain = os.getenv('ORG_DOMAIN', 'example.com')
        self.org_name = os.getenv('ORG_NAME', 'TPS Organization')
        self.org_phone_prefix = os.getenv('ORG_PHONE_PREFIX', '+31 6')
        self.org_employee_id_prefix = os.getenv('ORG_EMPLOYEE_ID_PREFIX', 'EMP')
        
        # Admin configuration
        self.admin_config = {
            'username': os.getenv('ADMIN_USERNAME', 'admin'),
            'email': os.getenv('ADMIN_EMAIL', f'admin@{self.org_domain}'),
            'password': os.getenv('ADMIN_PASSWORD'),
            'first_name': os.getenv('ADMIN_FIRST_NAME', 'System'),
            'last_name': os.getenv('ADMIN_LAST_NAME', 'Administrator'),
        }
        
        # Test data configuration
        self.test_config = {
            'create_test_users': os.getenv('CREATE_TEST_USERS', 'False').lower() == 'true',
            'test_user_count': int(os.getenv('TEST_USER_COUNT', '8')),
            'test_password': os.getenv('TEST_PASSWORD', 'secure-test-password'),
        }
    
    @staticmethod
    def generate_secret_key():
        """Generate a new Django secret key"""
        return get_random_secret_key()
    
    @staticmethod
    def generate_secure_password(length=16):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def get_admin_config(self):
        """Get admin user configuration with secure defaults"""
        config = self.admin_config.copy()
        
        # Generate secure password if not provided
        if not config['password']:
            if self.environment == 'development':
                config['password'] = 'admin123'  # Simple for development
            else:
                raise ValueError(
                    "ADMIN_PASSWORD must be set in production environment. "
                    f"Generate one with: python -c \"import secrets; print('{self.generate_secure_password()}')\""
                )
        
        return config
    
    def get_test_config(self):
        """Get test data configuration"""
        return self.test_config
    
    def generate_test_email(self, username):
        """Generate a test email address"""
        if self.environment == 'development':
            return f'{username}@{self.test_domain}'
        else:
            return self.fake.email()
    
    def generate_employee_id(self, sequence_number, role_prefix='EMP'):
        """Generate an employee ID"""
        return f'{role_prefix}{sequence_number:03d}'
    
    def generate_phone_number(self):
        """Generate a phone number using org prefix"""
        if self.org_phone_prefix.startswith('+31'):
            # Dutch format
            number = secrets.randbelow(90000000) + 10000000
            return f'{self.org_phone_prefix} {number}'
        else:
            return self.fake.phone_number()
    
    def get_organization_config(self):
        """Get organization configuration"""
        return {
            'name': self.org_name,
            'domain': self.org_domain,
            'phone_prefix': self.org_phone_prefix,
            'employee_id_prefix': self.org_employee_id_prefix,
        }
    
    def validate_environment(self):
        """Validate that required environment variables are set"""
        errors = []
        
        # Check required settings for production
        if self.environment == 'production':
            required_vars = [
                'SECRET_KEY',
                'ADMIN_PASSWORD',
                'ORG_DOMAIN',
            ]
            
            for var in required_vars:
                if not os.getenv(var):
                    errors.append(f"Environment variable '{var}' is required in production")
        
        # Check SECRET_KEY is not the default
        secret_key = os.getenv('SECRET_KEY', '')
        if 'django-insecure' in secret_key:
            errors.append("SECRET_KEY appears to be a default Django key. Generate a new one for security.")
        
        return errors


# Global configuration manager instance
config_manager = ConfigManager()