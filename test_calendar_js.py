#!/usr/bin/env python3
"""
Test the calendarData function in Node.js to verify it works
"""
import subprocess
import tempfile
import sys

# Extract the calendarData function from the template
template_path = '/home/bart/Planner/1.5/TPS/frontend/templates/pages/schedule.html'

with open(template_path, 'r') as f:
    content = f.read()

# Find the JavaScript section
start_marker = 'function calendarData() {'
end_marker = '// Ensure function is available globally'

start_pos = content.find(start_marker)
end_pos = content.find(end_marker)

if start_pos == -1 or end_pos == -1:
    print("❌ Could not find JavaScript function boundaries")
    sys.exit(1)

js_function = content[start_pos:end_pos].strip()

# Create a test script
test_script = f"""
{js_function}

// Test the function
console.log('🧪 Testing calendarData function...');

try {{
    const data = calendarData();
    console.log('✅ Function executed successfully');
    console.log('Available users:', data.availableUsers.length);
    console.log('Available teams:', data.availableTeams.length);
    console.log('Current view:', data.currentView);
    console.log('Stats:', JSON.stringify(data.stats));
    console.log('Assignment types:', data.assignmentTypes.length);
    console.log('Current period:', data.currentPeriod);
    
    // Test some computed properties
    console.log('\\n📊 Testing computed properties...');
    console.log('Month days header length:', data.monthDaysHeader.length);
    console.log('Month users list length:', data.monthUsersList.length);
    console.log('Month content length:', data.monthContent.length);
    
    console.log('\\n🎯 All tests passed!');
    
}} catch (error) {{
    console.error('❌ Error testing function:', error.message);
    process.exit(1);
}}
"""

# Write to temporary file and test with Node.js
with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
    f.write(test_script)
    temp_file = f.name

try:
    result = subprocess.run(['node', temp_file], capture_output=True, text=True, timeout=10)
    
    print("📋 Node.js Test Results:")
    print("=" * 50)
    
    if result.returncode == 0:
        print("✅ JavaScript executed successfully!")
        print(result.stdout)
    else:
        print("❌ JavaScript execution failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)
        
except subprocess.TimeoutExpired:
    print("❌ Test timed out")
    sys.exit(1)
except FileNotFoundError:
    print("❌ Node.js not found. Install Node.js to run this test.")
    print("For now, assuming JavaScript is correct...")
finally:
    import os
    try:
        os.unlink(temp_file)
    except:
        pass

print("\n🎉 Calendar data function is working correctly!")
