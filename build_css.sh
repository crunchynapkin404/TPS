#!/bin/bash

# TPS V1.4 - CSS Build Script
# This script builds the Tailwind CSS and collects static files

echo "🎨 Building TPS CSS..."

# Navigate to theme directory
cd theme/static_src

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Build Tailwind CSS
echo "🔧 Compiling Tailwind CSS..."
npm run build

# Go back to project root
cd ../..

# Copy built CSS to frontend static directory
echo "📋 Copying CSS to frontend static directory..."
mkdir -p frontend/static/css
cp theme/static/css/styles.css frontend/static/css/

# Copy JavaScript files to frontend static directory
echo "📋 Copying JavaScript files..."
mkdir -p frontend/static/js/vendor
cp theme/static_src/src/js/base.js frontend/static/js/
cp theme/static_src/src/js/dashboard.js frontend/static/js/

# Download Alpine.js if it doesn't exist
if [ ! -f "frontend/static/js/vendor/alpine.min.js" ]; then
    echo "⬇️ Downloading Alpine.js..."
    wget -q https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js -O frontend/static/js/vendor/alpine.min.js
    if [ $? -eq 0 ]; then
        echo "✅ Alpine.js downloaded successfully"
    else
        echo "❌ Failed to download Alpine.js"
        exit 1
    fi
else
    echo "✅ Alpine.js already exists"
fi

# Collect static files (only if Django is available)
if command -v python &> /dev/null && python -c "import django" 2>/dev/null; then
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "⚠️ Django not available, skipping collectstatic"
fi

echo "✅ CSS build complete!"
echo "🚀 Your TPS application is ready with the latest styles."
echo ""
echo "📊 Build Summary:"
echo "   - Tailwind CSS: $(wc -c < theme/static/css/styles.css) bytes"
echo "   - Alpine.js: $(wc -c < frontend/static/js/vendor/alpine.min.js) bytes"
echo "   - Base JS: $(wc -c < frontend/static/js/base.js) bytes"