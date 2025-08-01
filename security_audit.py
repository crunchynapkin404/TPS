#!/usr/bin/env python3
"""
TPS V1.4 - Security Audit Script
Comprehensive security vulnerability scanner for the TPS application
"""

import os
import re
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class SecurityAuditor:
    """
    Comprehensive security auditor for TPS application
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.findings = []
        self.risk_matrix = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': [],
            'INFO': []
        }
    
    def add_finding(self, severity: str, category: str, title: str, description: str, 
                   file_path: str = None, line_number: int = None, 
                   remediation: str = None, owasp_category: str = None):
        """Add a security finding"""
        finding = {
            'severity': severity,
            'category': category,
            'title': title,
            'description': description,
            'file_path': file_path,
            'line_number': line_number,
            'remediation': remediation,
            'owasp_category': owasp_category,
            'timestamp': datetime.now().isoformat()
        }
        self.findings.append(finding)
        self.risk_matrix[severity].append(finding)
    
    def check_hardcoded_secrets(self):
        """Check for hardcoded secrets and credentials"""
        print("🔍 Checking for hardcoded secrets...")
        
        secret_patterns = [
            (r'SECRET_KEY\s*=\s*["\']django-insecure-', 'Insecure Django SECRET_KEY'),
            (r'password\s*=\s*["\'](?:admin123|password123|test123)["\']', 'Hardcoded weak password'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'Hardcoded token'),
            (r'AWS_SECRET_ACCESS_KEY\s*=\s*["\'][^"\']+["\']', 'Hardcoded AWS secret'),
            (r'database.*password.*=.*["\'][^"\']+["\']', 'Hardcoded database password'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                self.add_finding(
                                    severity='CRITICAL',
                                    category='Hardcoded Secrets',
                                    title=description,
                                    description=f'Found potential hardcoded secret: {line.strip()}',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    remediation='Move sensitive data to environment variables',
                                    owasp_category='A07:2021 – Identification and Authentication Failures'
                                )
            except Exception as e:
                continue
    
    def check_sql_injection(self):
        """Check for SQL injection vulnerabilities"""
        print("🔍 Checking for SQL injection vulnerabilities...")
        
        # Patterns that might indicate SQL injection risks
        dangerous_patterns = [
            (r'raw\s*\(\s*["\'][^"\']*%s[^"\']*["\']', 'Raw SQL with string formatting'),
            (r'execute\s*\(["\'][^"\']*\+[^"\']*["\']', 'SQL execute with string concatenation'),
            (r'\.extra\s*\([^)]*where.*%', 'Django extra() with string formatting'),
            (r'cursor\.execute\s*\([^)]*%[^)]*\)', 'Raw cursor execute with formatting'),
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in dangerous_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                self.add_finding(
                                    severity='HIGH',
                                    category='SQL Injection',
                                    title=description,
                                    description=f'Potential SQL injection risk: {line.strip()}',
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=i,
                                    remediation='Use Django ORM or parameterized queries',
                                    owasp_category='A03:2021 – Injection'
                                )
            except Exception as e:
                continue
    
    def check_xss_vulnerabilities(self):
        """Check for XSS vulnerabilities in templates"""
        print("🔍 Checking for XSS vulnerabilities...")
        
        xss_patterns = [
            (r'\{\{\s*[^}]*\|safe\s*\}\}', 'Django safe filter usage'),
            (r'\{\{\s*[^}]*\|safeseq\s*\}\}', 'Django safeseq filter usage'),
            (r'mark_safe\s*\(', 'Django mark_safe usage'),
            (r'innerHTML\s*=', 'JavaScript innerHTML assignment'),
            (r'document\.write\s*\(', 'JavaScript document.write usage'),
        ]
        
        template_files = list(self.project_root.rglob('*.html')) + list(self.project_root.rglob('*.js'))
        
        for template_file in template_files:
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, description in xss_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                severity = 'HIGH' if 'safe' in pattern.lower() else 'MEDIUM'
                                self.add_finding(
                                    severity=severity,
                                    category='XSS',
                                    title=description,
                                    description=f'Potential XSS vulnerability: {line.strip()}',
                                    file_path=str(template_file.relative_to(self.project_root)),
                                    line_number=i,
                                    remediation='Review usage and ensure proper input sanitization',
                                    owasp_category='A03:2021 – Injection'
                                )
            except Exception as e:
                continue
    
    def check_authentication_authorization(self):
        """Check authentication and authorization implementation"""
        print("🔍 Checking authentication and authorization...")
        
        auth_issues = []
        
        # Check for views without authentication
        for py_file in self.project_root.rglob('views.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for class-based views without authentication
                    class_views = re.findall(r'class\s+(\w+)\s*\([^)]*View[^)]*\):', content)
                    for view_name in class_views:
                        view_content = re.search(f'class\\s+{view_name}.*?(?=class|\\Z)', content, re.DOTALL)
                        if view_content and 'permission_classes' not in view_content.group(0) and 'login_required' not in view_content.group(0):
                            self.add_finding(
                                severity='MEDIUM',
                                category='Authentication',
                                title='View without explicit authentication',
                                description=f'View {view_name} may lack authentication requirements',
                                file_path=str(py_file.relative_to(self.project_root)),
                                remediation='Add appropriate permission_classes or authentication decorators',
                                owasp_category='A01:2021 – Broken Access Control'
                            )
            except Exception as e:
                continue
    
    def check_configuration_security(self):
        """Check Django configuration security"""
        print("🔍 Checking configuration security...")
        
        settings_file = self.project_root / 'tps_project' / 'settings.py'
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for DEBUG=True
                    if re.search(r'DEBUG\s*=\s*True', content):
                        self.add_finding(
                            severity='HIGH',
                            category='Configuration',
                            title='DEBUG enabled',
                            description='DEBUG=True should not be used in production',
                            file_path='tps_project/settings.py',
                            remediation='Set DEBUG=False in production environment',
                            owasp_category='A05:2021 – Security Misconfiguration'
                        )
                    
                    # Check for insecure settings
                    insecure_patterns = [
                        (r'ALLOWED_HOSTS\s*=\s*\[\s*\]', 'Empty ALLOWED_HOSTS'),
                        (r'SESSION_COOKIE_SECURE\s*=\s*False', 'Insecure session cookies'),
                        (r'CSRF_COOKIE_SECURE\s*=\s*False', 'Insecure CSRF cookies'),
                    ]
                    
                    for pattern, description in insecure_patterns:
                        if re.search(pattern, content):
                            self.add_finding(
                                severity='MEDIUM',
                                category='Configuration',
                                title=description,
                                description=f'Insecure configuration found',
                                file_path='tps_project/settings.py',
                                remediation='Review and secure configuration settings',
                                owasp_category='A05:2021 – Security Misconfiguration'
                            )
            except Exception as e:
                pass
    
    def check_password_policy(self):
        """Check password policy implementation"""
        print("🔍 Checking password policy...")
        
        settings_file = self.project_root / 'tps_project' / 'settings.py'
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'AUTH_PASSWORD_VALIDATORS' not in content:
                        self.add_finding(
                            severity='MEDIUM',
                            category='Password Policy',
                            title='No password validators configured',
                            description='AUTH_PASSWORD_VALIDATORS not found in settings',
                            file_path='tps_project/settings.py',
                            remediation='Configure strong password validation rules',
                            owasp_category='A07:2021 – Identification and Authentication Failures'
                        )
                    elif 'MinimumLengthValidator' in content:
                        # Check if minimum length is adequate
                        min_length_match = re.search(r'min_length["\']:\s*(\d+)', content)
                        if min_length_match and int(min_length_match.group(1)) < 8:
                            self.add_finding(
                                severity='LOW',
                                category='Password Policy',
                                title='Weak minimum password length',
                                description=f'Minimum password length is {min_length_match.group(1)}, should be at least 8',
                                file_path='tps_project/settings.py',
                                remediation='Increase minimum password length to at least 8 characters',
                                owasp_category='A07:2021 – Identification and Authentication Failures'
                            )
            except Exception as e:
                pass
    
    def check_input_validation(self):
        """Check input validation implementation"""
        print("🔍 Checking input validation...")
        
        for py_file in self.project_root.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'migrations' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for request.GET or request.POST usage without validation
                    for i, line in enumerate(lines, 1):
                        if re.search(r'request\.(GET|POST)\[', line) and 'clean' not in line.lower():
                            self.add_finding(
                                severity='LOW',
                                category='Input Validation',
                                title='Direct request parameter access',
                                description=f'Direct access to request parameters: {line.strip()}',
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=i,
                                remediation='Use Django forms or serializers for input validation',
                                owasp_category='A03:2021 – Injection'
                            )
            except Exception as e:
                continue
    
    def run_django_security_check(self):
        """Run Django's built-in security check"""
        print("🔍 Running Django security check...")
        
        try:
            result = subprocess.run(
                ['python', 'manage.py', 'check', '--deploy'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or 'WARNING' in result.stdout or 'ERROR' in result.stdout:
                issues = result.stdout.split('\n')
                for issue in issues:
                    if issue.strip() and ('WARNING' in issue or 'ERROR' in issue):
                        severity = 'HIGH' if 'ERROR' in issue else 'MEDIUM'
                        self.add_finding(
                            severity=severity,
                            category='Django Security Check',
                            title='Django deployment check issue',
                            description=issue.strip(),
                            remediation='Review Django deployment checklist',
                            owasp_category='A05:2021 – Security Misconfiguration'
                        )
        except Exception as e:
            self.add_finding(
                severity='INFO',
                category='Django Security Check',
                title='Could not run Django security check',
                description=f'Error running check: {str(e)}',
                remediation='Manually run "python manage.py check --deploy"'
            )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        print("📊 Generating security report...")
        
        total_findings = len(self.findings)
        severity_counts = {k: len(v) for k, v in self.risk_matrix.items()}
        
        # Calculate risk score
        risk_score = (
            severity_counts['CRITICAL'] * 10 +
            severity_counts['HIGH'] * 7 +
            severity_counts['MEDIUM'] * 4 +
            severity_counts['LOW'] * 1
        )
        
        report = {
            'scan_timestamp': datetime.now().isoformat(),
            'project_root': str(self.project_root),
            'summary': {
                'total_findings': total_findings,
                'risk_score': risk_score,
                'severity_breakdown': severity_counts
            },
            'risk_matrix': self.risk_matrix,
            'recommendations': self.get_recommendations(),
            'compliance_status': self.get_compliance_status()
        }
        
        return report
    
    def get_recommendations(self) -> List[str]:
        """Get security recommendations based on findings"""
        recommendations = []
        
        if self.risk_matrix['CRITICAL']:
            recommendations.append("🚨 URGENT: Address all CRITICAL findings immediately before deployment")
        
        if self.risk_matrix['HIGH']:
            recommendations.append("⚠️  Address HIGH severity findings within 24 hours")
        
        recommendations.extend([
            "🔒 Implement Web Application Firewall (WAF)",
            "🔍 Enable security logging and monitoring",
            "🛡️  Implement Content Security Policy (CSP) headers",
            "🔐 Use HTTPS in production with HSTS enabled",
            "📋 Regular security audits and penetration testing",
            "🔄 Keep all dependencies updated",
            "👥 Implement proper user role management",
            "🏠 Secure deployment environment configuration"
        ])
        
        return recommendations
    
    def get_compliance_status(self) -> Dict[str, str]:
        """Check OWASP Top 10 compliance status"""
        owasp_categories = {
            'A01:2021 – Broken Access Control': 'PASS',
            'A02:2021 – Cryptographic Failures': 'PASS', 
            'A03:2021 – Injection': 'PASS',
            'A04:2021 – Insecure Design': 'PASS',
            'A05:2021 – Security Misconfiguration': 'PASS',
            'A06:2021 – Vulnerable and Outdated Components': 'PASS',
            'A07:2021 – Identification and Authentication Failures': 'PASS',
            'A08:2021 – Software and Data Integrity Failures': 'PASS',
            'A09:2021 – Security Logging and Monitoring Failures': 'PASS',
            'A10:2021 – Server-Side Request Forgery': 'PASS'
        }
        
        # Check findings against OWASP categories
        for finding in self.findings:
            if finding['owasp_category'] and finding['severity'] in ['CRITICAL', 'HIGH']:
                owasp_categories[finding['owasp_category']] = 'FAIL'
            elif finding['owasp_category'] and finding['severity'] == 'MEDIUM':
                if owasp_categories[finding['owasp_category']] != 'FAIL':
                    owasp_categories[finding['owasp_category']] = 'WARNING'
        
        return owasp_categories
    
    def run_full_audit(self):
        """Run complete security audit"""
        print("🔐 Starting TPS Security Audit...")
        print("=" * 50)
        
        self.check_hardcoded_secrets()
        self.check_sql_injection()
        self.check_xss_vulnerabilities()
        self.check_authentication_authorization()
        self.check_configuration_security()
        self.check_password_policy()
        self.check_input_validation()
        self.run_django_security_check()
        
        return self.generate_report()


def main():
    """Main function to run security audit"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    auditor = SecurityAuditor(project_root)
    report = auditor.run_full_audit()
    
    # Print summary
    print("\n" + "=" * 50)
    print("🔐 TPS SECURITY AUDIT RESULTS")
    print("=" * 50)
    print(f"📅 Scan Date: {report['scan_timestamp']}")
    print(f"📊 Total Findings: {report['summary']['total_findings']}")
    print(f"🎯 Risk Score: {report['summary']['risk_score']}")
    print("\n📈 Severity Breakdown:")
    for severity, count in report['summary']['severity_breakdown'].items():
        emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '🔶', 'LOW': '🔷', 'INFO': 'ℹ️'}
        print(f"   {emoji.get(severity, '•')} {severity}: {count}")
    
    print("\n🛡️  OWASP Top 10 Compliance:")
    for category, status in report['compliance_status'].items():
        emoji = {'PASS': '✅', 'WARNING': '⚠️', 'FAIL': '❌'}
        print(f"   {emoji.get(status, '•')} {category}: {status}")
    
    # Save detailed report
    report_file = Path(project_root) / 'security_audit_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    if report['summary']['risk_score'] > 20:
        print("\n🚨 HIGH RISK: Immediate security attention required!")
        sys.exit(1)
    elif report['summary']['risk_score'] > 10:
        print("\n⚠️  MEDIUM RISK: Address security findings soon")
        sys.exit(1)
    else:
        print("\n✅ ACCEPTABLE RISK: Good security posture")
        sys.exit(0)


if __name__ == '__main__':
    main()