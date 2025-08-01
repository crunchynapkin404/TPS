#!/usr/bin/env python
"""
Simple script to test if the schedule template has JavaScript syntax errors
"""
import re

def check_javascript_syntax(template_path):
    """Check for obvious JavaScript syntax errors in template"""
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Extract JavaScript content
    js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    
    issues = []
    
    for i, js_block in enumerate(js_blocks):
        # Skip empty blocks or those that are just comments
        if not js_block.strip() or js_block.strip().startswith('//'):
            continue
            
        # Check for basic syntax issues
        lines = js_block.split('\n')
        
        brace_count = 0
        paren_count = 0
        bracket_count = 0
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Count braces, parentheses, brackets
            brace_count += line.count('{') - line.count('}')
            paren_count += line.count('(') - line.count(')')
            bracket_count += line.count('[') - line.count(']')
            
            # Check for common issues
            if line.endswith(',}') or line.endswith(',]'):
                issues.append(f"JS Block {i+1}, Line {line_num}: Trailing comma before closing brace/bracket")
            
            if '...' in line and 'console.log' not in line:
                issues.append(f"JS Block {i+1}, Line {line_num}: Potential ellipsis/incomplete code: {line[:50]}")
        
        # Check final balance
        if brace_count != 0:
            issues.append(f"JS Block {i+1}: Unbalanced braces (diff: {brace_count})")
        if paren_count != 0:
            issues.append(f"JS Block {i+1}: Unbalanced parentheses (diff: {paren_count})")
        if bracket_count != 0:
            issues.append(f"JS Block {i+1}: Unbalanced brackets (diff: {bracket_count})")
    
    return issues

if __name__ == '__main__':
    template_path = '/home/bart/Planner/1.5/TPS/frontend/templates/pages/schedule.html'
    issues = check_javascript_syntax(template_path)
    
    if issues:
        print("JavaScript Syntax Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No obvious JavaScript syntax issues found!")
    
    # Also check for Django template syntax issues
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Look for problematic template syntax
    django_issues = []
    
    if '{% now ' in content:
        django_issues.append("Found {% now %} template tag usage")
    
    if django_issues:
        print("\nDjango Template Issues:")
        for issue in django_issues:
            print(f"  - {issue}")
