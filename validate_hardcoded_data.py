#!/usr/bin/env python3
"""
TPS Hardcoded Data Scanner
Scans the repository for remaining hardcoded non-real database data
"""

import os
import re
import sys
from pathlib import Path


class HardcodedDataScanner:
    """Scanner for hardcoded data patterns"""
    
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.issues = []
        
        # Patterns to detect hardcoded data
        self.patterns = {
            'passwords': [
                r'password.*=.*["\'](?:admin123|password123|tps2024!|testpass123)["\']',
                r'["\'](?:admin123|password123|tps2024!|testpass123)["\']',
            ],
            'secret_keys': [
                r'django-insecure-[a-z0-9@!#$%^&*()_+\-=\[\]{}|;\':",./<>?~`]+',
                r'SECRET_KEY.*=.*["\']django-insecure-',
            ],
            'emails': [
                r'[a-zA-Z0-9._%+-]+@(?:example\.com|test\.com)',
                r'admin@(?:example\.com|test\.com|tps\.local)',
            ],
            'employee_ids': [
                r'["\'](?:ADM001|ENG00[1-9]|PLN001|MGR001|USER001|ADMIN001)["\']',
            ],
            'phone_numbers': [
                r'\+31\s*(?:20\s*)?1234567',
                r'\+31\s*6\s*\d{8}',  # Only flag if it's the same pattern repeatedly
            ],
            'database_urls': [
                r'sqlite:///[^\'\"]*db\.sqlite3',
                r'postgresql://[^\'\"]*',
            ]
        }
        
        # Files to exclude from scanning
        self.exclude_patterns = [
            r'\.git/',
            r'__pycache__/',
            r'\.pyc$',
            r'\.log$',
            r'node_modules/',
            r'staticfiles/',
            r'\.env$',  # Exclude the actual .env file
            r'HARDCODED_DATA_REMEDIATION_REPORT\.md$',  # Our report file
            r'validate_hardcoded_data\.py$',  # This script itself
        ]
    
    def should_exclude(self, file_path):
        """Check if file should be excluded from scanning"""
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in self.exclude_patterns)
    
    def scan_file(self, file_path):
        """Scan a single file for hardcoded data"""
        if self.should_exclude(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for category, patterns in self.patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Calculate line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Get the line content
                        lines = content.split('\n')
                        line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                        
                        # Skip acceptable hardcoded values
                        if self.is_acceptable_hardcoded_value(file_path, line_content, match.group(), category):
                            continue
                        
                        self.issues.append({
                            'file': str(file_path.relative_to(self.repo_path)),
                            'line': line_num,
                            'category': category,
                            'pattern': pattern,
                            'match': match.group(),
                            'line_content': line_content
                        })
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
    
    def is_acceptable_hardcoded_value(self, file_path, line_content, match, category):
        """Check if a hardcoded value is acceptable (templates, fallbacks, etc.)"""
        file_str = str(file_path)
        
        # Template files (.env.example, .env.template) are allowed to have examples
        if '.env.example' in file_str or '.env.template' in file_str:
            return True
        
        # Configuration files with fallbacks and warnings are acceptable
        if 'config.py' in file_str and 'development' in line_content:
            return True
        
        # Settings files with clear warnings and fallback values
        if 'settings' in file_str and ('fallback' in line_content.lower() or 'warning' in line_content.lower() or 'testing-only' in line_content or 'dev-only' in line_content):
            return True
        
        # Comments in source code explaining patterns
        if line_content.strip().startswith('#'):
            return True
        
        # Database URL examples in comments
        if category == 'database_urls' and ('#' in line_content or 'example' in line_content.lower()):
            return True
        
        return False
    
    def scan_directory(self):
        """Scan all files in the repository"""
        print(f"Scanning repository: {self.repo_path}")
        
        # Scan Python files, configuration files, and other relevant files
        file_patterns = ['*.py', '*.env*', '*.yml', '*.yaml', '*.json', '*.txt', '*.md']
        
        for pattern in file_patterns:
            for file_path in self.repo_path.rglob(pattern):
                if file_path.is_file():
                    self.scan_file(file_path)
    
    def generate_report(self):
        """Generate a report of found issues"""
        if not self.issues:
            print("✅ SUCCESS: No hardcoded data found!")
            return True
        
        print(f"❌ FOUND {len(self.issues)} POTENTIAL HARDCODED DATA ISSUES:")
        print("=" * 80)
        
        # Group by category
        by_category = {}
        for issue in self.issues:
            category = issue['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(issue)
        
        for category, issues in by_category.items():
            print(f"\n📂 {category.upper()} ({len(issues)} issues):")
            for issue in issues:
                print(f"  📄 {issue['file']}:{issue['line']}")
                print(f"     Match: {issue['match']}")
                print(f"     Line:  {issue['line_content']}")
                print()
        
        return False
    
    def validate_configuration(self):
        """Validate that configuration system is working"""
        print("\n🔧 VALIDATING CONFIGURATION SYSTEM:")
        
        # Check for required files
        required_files = [
            '.env.template',
            'core/config.py',
            'HARDCODED_DATA_REMEDIATION_REPORT.md'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.repo_path / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing configuration files: {', '.join(missing_files)}")
            return False
        
        print("✅ All required configuration files present")
        
        # Check that .env.template has required variables
        template_path = self.repo_path / '.env.template'
        required_vars = ['SECRET_KEY', 'ADMIN_PASSWORD', 'ORG_DOMAIN']
        
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            missing_vars = []
            for var in required_vars:
                if var not in template_content:
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"❌ Missing required variables in .env.template: {', '.join(missing_vars)}")
                return False
            
            print("✅ .env.template contains all required variables")
        except Exception as e:
            print(f"❌ Error reading .env.template: {e}")
            return False
        
        return True


def main():
    """Main execution"""
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = '.'
    
    scanner = HardcodedDataScanner(repo_path)
    
    print("🔍 TPS HARDCODED DATA VALIDATION")
    print("=" * 50)
    
    # Scan for hardcoded data
    scanner.scan_directory()
    scan_success = scanner.generate_report()
    
    # Validate configuration system
    config_success = scanner.validate_configuration()
    
    # Overall result
    print("\n" + "=" * 50)
    if scan_success and config_success:
        print("🎉 VALIDATION PASSED: Repository is secure and properly configured!")
        return 0
    else:
        print("⚠️  VALIDATION FAILED: Issues found that need attention")
        return 1


if __name__ == '__main__':
    sys.exit(main())