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

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ CSS build complete!"
echo "🚀 Your TPS application is ready with the latest styles."