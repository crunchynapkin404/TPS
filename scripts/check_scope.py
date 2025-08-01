#!/usr/bin/env python3
"""
Test Django template rendering
"""
import os
import sys
import re

def check_alpine_scope():
    """Check if Alpine.js bindings are within proper scope"""
    template_path = '/home/bart/Planner/1.5/TPS/frontend/templates/pages/schedule.html'
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Find the main Alpine.js container
    main_container_start = content.find('x-data="calendarData()"')
    if main_container_start == -1:
        print("❌ Main Alpine.js container not found")
        return False
    
    print(f"✅ Main Alpine.js container found at position {main_container_start}")
    
    # Find the end of the main container
    # Count opening/closing div tags after the main container
    lines = content.splitlines()
    container_line = -1
    
    for i, line in enumerate(lines):
        if 'x-data="calendarData()"' in line:
            container_line = i
            break
    
    if container_line == -1:
        print("❌ Could not find container line")
        return False
    
    print(f"✅ Container starts at line {container_line + 1}")
    
    # Find Alpine.js bindings
    bindings = [
        'x-show="showAssignmentModal',
        'x-model="assignmentForm',
        'availableUsers',
        'assignmentTypes',
        'isCreating'
    ]
    
    binding_lines = {}
    for binding in bindings:
        for i, line in enumerate(lines):
            if binding in line:
                binding_lines[binding] = i + 1
                break
    
    print("\n📍 Alpine.js bindings found:")
    for binding, line_num in binding_lines.items():
        status = "✅" if line_num > container_line else "❌"
        print(f"  {status} {binding}: line {line_num}")
    
    # Check if modal is inside container
    modal_line = -1
    for i, line in enumerate(lines):
        if 'showAssignmentModal' in line and 'x-show' in line:
            modal_line = i + 1
            break
    
    if modal_line == -1:
        print("❌ Modal not found")
        return False
    
    print(f"\n🎯 Modal location: line {modal_line}")
    print(f"   Container starts: line {container_line + 1}")
    print(f"   Modal is {'✅ INSIDE' if modal_line > container_line else '❌ OUTSIDE'} container")
    
    return modal_line > container_line

if __name__ == '__main__':
    success = check_alpine_scope()
    print(f"\n{'✅ All Alpine.js bindings are properly scoped!' if success else '❌ Alpine.js scope issues detected!'}")
    sys.exit(0 if success else 1)
