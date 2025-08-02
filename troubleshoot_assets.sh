#!/bin/bash

# TPS V1.4 - Asset Troubleshooting Script
# This script checks and fixes common CSS/JS issues

echo "🔍 TPS Asset Troubleshooting Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    case $1 in
        "ok") echo -e "${GREEN}✅ $2${NC}" ;;
        "warn") echo -e "${YELLOW}⚠️  $2${NC}" ;;
        "error") echo -e "${RED}❌ $2${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $2${NC}" ;;
    esac
}

# Function to check file existence and size
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        local size=$(wc -c < "$file")
        if [ $size -gt 0 ]; then
            print_status "ok" "$description exists ($size bytes)"
            return 0
        else
            print_status "error" "$description exists but is empty"
            return 1
        fi
    else
        print_status "error" "$description missing"
        return 1
    fi
}

# Function to check directory existence
check_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        print_status "ok" "$description exists"
        return 0
    else
        print_status "error" "$description missing"
        return 1
    fi
}

echo "1. Checking Directory Structure"
echo "------------------------------"

# Check critical directories
check_directory "theme/static_src" "Tailwind source directory"
check_directory "theme/static_src/node_modules" "Node modules"
check_directory "frontend/static" "Frontend static directory"
check_directory "frontend/static/css" "Frontend CSS directory"
check_directory "frontend/static/js" "Frontend JS directory"
check_directory "frontend/static/js/vendor" "Frontend vendor JS directory"

echo ""
echo "2. Checking Critical Files"
echo "-------------------------"

# Check source files
check_file "theme/static_src/package.json" "Package.json"
check_file "theme/static_src/tailwind.config.js" "Tailwind config"
check_file "theme/static_src/src/styles.css" "Tailwind source CSS"

# Check built files
check_file "theme/static/css/styles.css" "Built Tailwind CSS (theme)"
check_file "frontend/static/css/styles.css" "Built Tailwind CSS (frontend)"
check_file "frontend/static/js/vendor/alpine.min.js" "Alpine.js"
check_file "frontend/static/js/base.js" "Base JavaScript"

echo ""
echo "3. Checking Dependencies"
echo "----------------------"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "ok" "Node.js $NODE_VERSION"
else
    print_status "error" "Node.js not found"
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_status "ok" "npm $NPM_VERSION"
else
    print_status "error" "npm not found"
fi

# Check Python
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    print_status "ok" "$PYTHON_VERSION"
else
    print_status "error" "Python not found"
fi

# Check Django
if python -c "import django" 2>/dev/null; then
    DJANGO_VERSION=$(python -c "import django; print(django.get_version())")
    print_status "ok" "Django $DJANGO_VERSION"
else
    print_status "error" "Django not found or not installed"
fi

echo ""
echo "4. Checking Build Process"
echo "------------------------"

# Check if Tailwind can build
cd theme/static_src 2>/dev/null
if [ $? -eq 0 ]; then
    if [ -f "package.json" ] && [ -d "node_modules" ]; then
        print_status "info" "Testing Tailwind build..."
        if npm run build &>/dev/null; then
            print_status "ok" "Tailwind build successful"
        else
            print_status "error" "Tailwind build failed"
        fi
    else
        print_status "warn" "Cannot test build - missing package.json or node_modules"
    fi
    cd ../..
else
    print_status "error" "Cannot access theme/static_src directory"
fi

echo ""
echo "5. Auto-Fix Common Issues"
echo "------------------------"

# Fix 1: Create missing directories
print_status "info" "Creating missing directories..."
mkdir -p frontend/static/{css,js,js/vendor}
print_status "ok" "Directories created"

# Fix 2: Download Alpine.js if missing
if [ ! -f "frontend/static/js/vendor/alpine.min.js" ]; then
    print_status "info" "Downloading Alpine.js..."
    if wget -q https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js -O frontend/static/js/vendor/alpine.min.js; then
        print_status "ok" "Alpine.js downloaded"
    else
        print_status "error" "Failed to download Alpine.js"
    fi
else
    print_status "ok" "Alpine.js already exists"
fi

# Fix 3: Copy built files if they exist
if [ -f "theme/static/css/styles.css" ]; then
    print_status "info" "Copying built CSS..."
    cp theme/static/css/styles.css frontend/static/css/
    print_status "ok" "CSS copied"
fi

if [ -f "theme/static_src/src/js/base.js" ]; then
    print_status "info" "Copying base JavaScript..."
    cp theme/static_src/src/js/base.js frontend/static/js/
    print_status "ok" "Base JavaScript copied"
fi

if [ -f "theme/static_src/src/js/dashboard.js" ]; then
    print_status "info" "Copying dashboard JavaScript..."
    cp theme/static_src/src/js/dashboard.js frontend/static/js/
    print_status "ok" "Dashboard JavaScript copied"
fi

echo ""
echo "6. Final Verification"
echo "--------------------"

# Final file checks
ISSUES=0

if ! check_file "frontend/static/css/styles.css" "Final CSS"; then
    ((ISSUES++))
fi

if ! check_file "frontend/static/js/vendor/alpine.min.js" "Final Alpine.js"; then
    ((ISSUES++))
fi

if ! check_file "frontend/static/js/base.js" "Final Base JS"; then
    ((ISSUES++))
fi

echo ""
echo "7. Summary & Recommendations"
echo "---------------------------"

if [ $ISSUES -eq 0 ]; then
    print_status "ok" "All critical files are present and non-empty"
    echo ""
    print_status "info" "Next steps:"
    echo "   1. Run: ./build_css.sh"
    echo "   2. If using Django: python manage.py collectstatic --noinput"
    echo "   3. Start your Django server: python manage.py runserver"
    echo ""
else
    print_status "error" "$ISSUES critical issues found"
    echo ""
    print_status "info" "Recommended fixes:"
    echo "   1. Install Node.js and npm if missing"
    echo "   2. Run: cd theme/static_src && npm install"
    echo "   3. Run: ./build_css.sh"
    echo "   4. Check Django settings for STATICFILES_DIRS configuration"
    echo ""
fi

# File size summary
echo "File Sizes:"
[ -f "frontend/static/css/styles.css" ] && echo "  - CSS: $(wc -c < frontend/static/css/styles.css) bytes"
[ -f "frontend/static/js/vendor/alpine.min.js" ] && echo "  - Alpine.js: $(wc -c < frontend/static/js/vendor/alpine.min.js) bytes"
[ -f "frontend/static/js/base.js" ] && echo "  - Base JS: $(wc -c < frontend/static/js/base.js) bytes"

echo ""
print_status "info" "Troubleshooting complete!"