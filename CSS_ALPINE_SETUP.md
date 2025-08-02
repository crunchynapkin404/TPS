# TPS CSS & Alpine.js Setup Guide

This document provides complete instructions for setting up and troubleshooting the TPS (Team Planning System) CSS and JavaScript assets.

## 🚀 Quick Start

For immediate setup, run these commands:

```bash
# Make scripts executable
chmod +x build_css.sh troubleshoot_assets.sh

# Run the build process
./build_css.sh

# If you encounter issues, run the troubleshooter
./troubleshoot_assets.sh
```

## 📁 Project Structure

```
TPS/
├── build_css.sh                 # Main build script
├── troubleshoot_assets.sh       # Troubleshooting script
├── theme/
│   ├── static_src/              # Source files for Tailwind
│   │   ├── package.json         # Node.js dependencies
│   │   ├── tailwind.config.js   # Tailwind configuration
│   │   ├── src/
│   │   │   ├── styles.css       # Main Tailwind CSS source
│   │   │   └── js/
│   │   │       ├── base.js      # Base JavaScript with Alpine.js stores
│   │   │       └── dashboard.js # Dashboard-specific JavaScript
│   │   └── node_modules/        # Node.js packages
│   └── static/
│       └── css/
│           └── styles.css       # Built Tailwind CSS (intermediate)
└── frontend/
    ├── templates/
    │   └── base.html            # Main template with asset references
    └── static/                  # Final static files directory
        ├── css/
        │   └── styles.css       # Final Tailwind CSS
        └── js/
            ├── base.js          # Alpine.js initialization
            ├── dashboard.js     # Dashboard functionality
            └── vendor/
                └── alpine.min.js # Alpine.js library (local)
```

## 🔧 Build Process

### Automated Build (Recommended)

```bash
./build_css.sh
```

This script:
1. Installs npm dependencies if needed
2. Compiles Tailwind CSS from source
3. Copies CSS to frontend static directory
4. Copies JavaScript files
5. Downloads Alpine.js if missing
6. Shows build summary

### Manual Build

If you prefer manual control:

```bash
# 1. Install dependencies
cd theme/static_src
npm install

# 2. Build Tailwind CSS
npm run build

# 3. Copy files
cd ../..
mkdir -p frontend/static/{css,js,js/vendor}
cp theme/static/css/styles.css frontend/static/css/
cp theme/static_src/src/js/*.js frontend/static/js/

# 4. Download Alpine.js (if not present)
wget -q https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js -O frontend/static/js/vendor/alpine.min.js
```

## 🛠️ Dependencies

### Required
- **Node.js** (v18+ recommended): For building Tailwind CSS
- **npm**: Comes with Node.js
- **Python** (3.8+ recommended): For Django
- **wget** or **curl**: For downloading Alpine.js

### Node.js Packages (auto-installed)
- `tailwindcss`: CSS framework
- `@tailwindcss/forms`: Form styling
- `@tailwindcss/typography`: Typography plugin

### JavaScript Libraries
- **Alpine.js v3.14.1**: Reactive JavaScript framework (downloaded automatically)

## 🎨 CSS Framework Features

### Tailwind CSS Configuration
- **Desktop-first approach**: Optimized for desktop interfaces
- **Dark mode support**: Class-based dark mode (`dark:` prefix)
- **Custom color palette**: TPS-branded colors
- **Component classes**: Pre-built UI components
- **European date/time formats**: Localized for European users

### Key Features
- Responsive grid system
- Dark mode support
- Custom TPS color scheme
- Typography scale optimized for desktop
- Form components with validation states
- Button variants and states
- Card components with hover effects
- Navigation components
- Status badges and indicators

## 🧩 Alpine.js Integration

### Global Stores
- **Notifications**: Toast-style notifications
- **Theme**: Dark/light mode toggle with persistence

### Key Features
- Reactive data binding
- Component state management
- Event handling
- DOM manipulation
- Local storage integration

## 🚨 Troubleshooting

### Common Issues

#### 1. "White page with black text and big icons"
**Causes:**
- CSS not loading properly
- Missing static files
- Django collectstatic not run

**Solutions:**
```bash
# Run the troubleshooter
./troubleshoot_assets.sh

# Rebuild everything
./build_css.sh

# If using Django
python manage.py collectstatic --noinput
```

#### 2. "Alpine.js not working"
**Causes:**
- CDN blocking
- Missing local Alpine.js file
- JavaScript errors

**Solutions:**
```bash
# Check if Alpine.js exists
ls -la frontend/static/js/vendor/alpine.min.js

# Download if missing
wget -q https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js -O frontend/static/js/vendor/alpine.min.js

# Check browser console for errors
```

#### 3. "Tailwind classes not working"
**Causes:**
- CSS not built
- Old cached CSS
- Missing file references

**Solutions:**
```bash
# Force rebuild
cd theme/static_src
npm run build
cd ../..
./build_css.sh

# Clear browser cache (Ctrl+F5)
```

#### 4. "Build fails with node errors"
**Causes:**
- Missing Node.js
- Outdated npm
- Missing dependencies

**Solutions:**
```bash
# Install Node.js (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Update npm
npm install -g npm@latest

# Reinstall dependencies
cd theme/static_src
rm -rf node_modules package-lock.json
npm install
```

### Diagnostic Commands

```bash
# Check all assets
./troubleshoot_assets.sh

# Check file sizes
wc -c frontend/static/css/styles.css
wc -c frontend/static/js/vendor/alpine.min.js

# Test Tailwind build
cd theme/static_src && npm run build

# Check Django static files
python manage.py findstatic css/styles.css
python manage.py findstatic js/vendor/alpine.min.js
```

### Browser Debugging

1. **Open Developer Tools** (F12)
2. **Check Console tab** for JavaScript errors  
3. **Check Network tab** for failed asset loads
4. **Check Elements tab** to verify classes are applied

### File Permissions

Ensure scripts are executable:
```bash
chmod +x build_css.sh troubleshoot_assets.sh
```

## 📦 Self-Contained Setup

This setup is completely self-contained and doesn't rely on external CDNs:

### ✅ What's Included
- ✅ Local Alpine.js (no CDN dependency)
- ✅ Complete Tailwind CSS build
- ✅ All JavaScript utilities
- ✅ Automated build process
- ✅ Troubleshooting tools

### ❌ No External Dependencies
- ❌ No CDN requests (except for initial Alpine.js download)
- ❌ No external font requests
- ❌ No third-party CSS frameworks

## 🔄 Development Workflow

### During Development
```bash
# Watch for changes (if you modify CSS/JS frequently)
cd theme/static_src
npm run dev  # Watches for changes and rebuilds automatically
```

### Before Deployment
```bash
# Production build
./build_css.sh

# Django static files collection
python manage.py collectstatic --noinput
```

### After Changes
```bash
# Rebuild everything
./build_css.sh

# Test in browser (clear cache with Ctrl+F5)
```

## 📝 Configuration Files

### `theme/static_src/package.json`
Contains npm dependencies and build scripts.

### `theme/static_src/tailwind.config.js`
Tailwind CSS configuration including:
- Content paths for purging unused CSS
- Custom color palette
- Plugin configuration
- Dark mode settings

### `frontend/templates/base.html`
Main template that loads all CSS and JavaScript assets.

## 🆘 Getting Help

If you still encounter issues after following this guide:

1. **Run the troubleshooter**: `./troubleshoot_assets.sh`
2. **Check the build output**: Look for error messages in the console
3. **Verify file permissions**: Ensure scripts are executable
4. **Check browser console**: Look for JavaScript errors
5. **Test with a fresh browser session**: Clear cache and cookies

## 📊 Performance Notes

### File Sizes (Typical)
- **Tailwind CSS**: ~94KB (minified)
- **Alpine.js**: ~45KB (minified)
- **Base JavaScript**: ~7KB

### Optimization
- CSS is minified in production
- Alpine.js is pre-compressed
- No unnecessary dependencies included

## 🔐 Security Considerations

- All assets are served locally (no CDN privacy concerns)
- No external script loading after initial setup
- Content Security Policy (CSP) friendly
- No inline JavaScript in templates