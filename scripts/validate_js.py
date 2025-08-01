#!/usr/bin/env python3
"""
Quick JavaScript validation script for Django template
"""
import re
import sys

def extract_javascript_from_template(file_path):
    """Extract JavaScript from Django template"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find JavaScript blocks
    js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    return '\n'.join(js_blocks)

def main():
    template_path = '/home/bart/Planner/1.5/TPS/frontend/templates/pages/schedule.html'
    
    try:
        js_content = extract_javascript_from_template(template_path)
        
        # Basic syntax checks
        open_braces = js_content.count('{')
        close_braces = js_content.count('}')
        
        print(f"JavaScript extraction successful!")
        print(f"Total lines: {len(js_content.splitlines())}")
        print(f"Open braces: {open_braces}")
        print(f"Close braces: {close_braces}")
        print(f"Brace balance: {'✅ BALANCED' if open_braces == close_braces else '❌ UNBALANCED'}")
        
        # Check for common issues
        if 'function calendarData(' in js_content:
            print("✅ calendarData function found")
        else:
            print("❌ calendarData function NOT found")
            
        if 'showAssignmentModal:' in js_content:
            print("✅ showAssignmentModal property found")
        else:
            print("❌ showAssignmentModal property NOT found")
            
        if 'availableUsers:' in js_content:
            print("✅ availableUsers property found")
        else:
            print("❌ availableUsers property NOT found")
            
        # Look for unterminated strings or other issues
        single_quotes = js_content.count("'")
        double_quotes = js_content.count('"')
        
        print(f"Single quotes: {single_quotes} ({'balanced' if single_quotes % 2 == 0 else 'unbalanced'})")
        print(f"Double quotes: {double_quotes} ({'balanced' if double_quotes % 2 == 0 else 'unbalanced'})")
        
        # Save extracted JS for inspection
        with open('/home/bart/Planner/1.5/TPS/extracted_js.js', 'w') as f:
            f.write(js_content)
        print("\n✅ JavaScript extracted to extracted_js.js for inspection")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
