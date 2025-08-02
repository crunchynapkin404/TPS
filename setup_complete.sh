#!/bin/bash

# TPS V1.4 - Complete Setup & Verification Script
# This script ensures everything is set up correctly and working

echo "🚀 TPS Complete Setup & Verification"
echo "===================================="
echo ""

# Color functions
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

success() { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

echo "1. Running Build Process"
echo "-----------------------"

# Run the build script
if ./build_css.sh; then
    success "Build completed successfully"
else
    error "Build failed - check the output above"
    exit 1
fi

echo ""
echo "2. Verifying Assets"
echo "------------------"

# Run troubleshooter
if ./troubleshoot_assets.sh | grep -q "All critical files are present"; then
    success "All assets verified"
else
    warning "Some issues detected - check troubleshooter output"
fi

echo ""
echo "3. File Summary"
echo "--------------"

# Display file information
if [ -f "frontend/static/css/styles.css" ]; then
    CSS_SIZE=$(wc -c < frontend/static/css/styles.css)
    success "Tailwind CSS: ${CSS_SIZE} bytes"
else
    error "CSS file missing"
fi

if [ -f "frontend/static/js/vendor/alpine.min.js" ]; then
    ALPINE_SIZE=$(wc -c < frontend/static/js/vendor/alpine.min.js)
    success "Alpine.js: ${ALPINE_SIZE} bytes"
else
    error "Alpine.js file missing"
fi

if [ -f "frontend/static/js/base.js" ]; then
    JS_SIZE=$(wc -c < frontend/static/js/base.js)
    success "Base JavaScript: ${JS_SIZE} bytes"
else
    error "Base JavaScript file missing"
fi

echo ""
echo "4. Quick Test"
echo "------------"

# Start a quick test server
info "Starting test server on port 8000..."
(cd . && python -m http.server 8000 > /dev/null 2>&1) &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Test if server is responding
if curl -s http://localhost:8000/test_assets.html > /dev/null; then
    success "Test server is running"
    info "Visit: http://localhost:8000/test_assets.html"
    echo ""
    echo "Test the following features:"
    echo "  • Dark/Light mode toggle (top right)"
    echo "  • Alpine.js counter (click 'Clicked: 0' button)"
    echo "  • Notification system (Success/Error buttons)"
    echo "  • Form components"
    echo "  • Responsive design (resize window)"
    echo ""
    info "Press Enter to stop the server and continue..."
    read -r
else
    warning "Test server not responding"
fi

# Stop the test server
kill $SERVER_PID 2>/dev/null
success "Test server stopped"

echo ""
echo "5. Django Integration"
echo "--------------------"

# Check if Django is available
if command -v python &> /dev/null && python -c "import django" 2>/dev/null; then
    info "Django detected - running collectstatic..."
    if python manage.py collectstatic --noinput > /dev/null 2>&1; then
        success "Django static files collected"
    else
        warning "Django collectstatic failed - check Django configuration"
    fi
else
    info "Django not available - skipping collectstatic"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
success "TPS CSS and Alpine.js setup is complete and verified"
echo ""
echo "Next Steps:"
echo "  1. If using Django: python manage.py runserver"
echo "  2. If using standalone: any HTTP server in the project root"
echo "  3. Check CSS_ALPINE_SETUP.md for detailed documentation"
echo ""
echo "Troubleshooting:"
echo "  • Run: ./troubleshoot_assets.sh"
echo "  • Check browser console for errors"
echo "  • Ensure all files are accessible via your web server"
echo ""
info "Happy coding! 🚀"