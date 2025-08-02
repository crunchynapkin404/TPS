# TPS Asset Management Scripts

This directory contains scripts for managing CSS and JavaScript assets in the TPS (Team Planning System) project.

## 🚀 Quick Start

Run this single command to set up everything:

```bash
./setup_complete.sh
```

## 📄 Scripts Overview

### `setup_complete.sh` 
**Complete setup and verification script**
- Runs the build process
- Verifies all assets
- Starts a test server
- Shows detailed status

### `build_css.sh`
**Main build script**
- Compiles Tailwind CSS
- Copies assets to correct locations
- Downloads Alpine.js if needed
- Shows build summary

### `troubleshoot_assets.sh`
**Comprehensive troubleshooting**
- Checks all directories and files
- Verifies dependencies
- Auto-fixes common issues
- Provides detailed diagnostics

## 📁 Key Files

- `CSS_ALPINE_SETUP.md` - Complete documentation
- `test_assets.html` - Test page for verifying everything works
- `frontend/static/` - Final location for all assets

## 🔧 Manual Build

If you prefer manual control:

```bash
# 1. Build CSS
cd theme/static_src
npm install
npm run build

# 2. Copy files
cd ../..
mkdir -p frontend/static/{css,js,js/vendor}
cp theme/static/css/styles.css frontend/static/css/
cp theme/static_src/src/js/*.js frontend/static/js/

# 3. Download Alpine.js
wget -q https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js -O frontend/static/js/vendor/alpine.min.js
```

## 🚨 If Something Goes Wrong

1. Run: `./troubleshoot_assets.sh`
2. Check the output for specific issues
3. Follow the recommended fixes
4. Re-run: `./build_css.sh`

## 📖 Full Documentation

See `CSS_ALPINE_SETUP.md` for complete documentation including:
- Detailed setup instructions
- Troubleshooting guide
- Architecture overview
- Development workflow