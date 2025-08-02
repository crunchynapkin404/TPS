# TPS V1.4 Design System

## Overview
The TPS (Team Planning System) uses a comprehensive design system built with Tailwind CSS and Alpine.js, providing a consistent, professional, and accessible user interface across all application pages.

## Design Principles
- **Desktop-First**: Optimized for desktop use with responsive mobile support
- **Accessibility**: WCAG compliant with proper ARIA labels and keyboard navigation
- **Consistency**: Unified design language across all pages and components
- **Performance**: Optimized CSS with minimal bundle size
- **Dark Mode Support**: Built-in dark mode with proper color contrasts

## Color System
### Primary Colors
- **Primary Blue**: `#2563eb` (blue-600) - Main brand color
- **Primary Dark**: `#1d4ed8` (blue-700) - Hover states
- **Primary Light**: `#93c5fd` (blue-300) - Backgrounds

### Semantic Colors
- **Success**: `#059669` (emerald-600) - Success states, confirmations
- **Warning**: `#d97706` (amber-600) - Warnings, pending states  
- **Error**: `#dc2626` (red-600) - Errors, critical actions
- **Info**: `#0284c7` (sky-600) - Information, neutral actions

### Role-Based Themes
- **Admin**: Red gradient theme for administrative functions
- **Manager**: Amber gradient theme for management functions
- **Planner**: Blue gradient theme for planning functions
- **User**: Purple gradient theme for general users

## Typography
- **Font Family**: Inter (with fallbacks to system fonts)
- **Base Size**: 16px for optimal readability
- **Scale**: Tailwind's default typographic scale
- **Line Height**: 1.6 for comfortable reading

## Component Library

### Buttons
```css
.btn - Base button class
.btn-primary - Primary action button (blue)
.btn-secondary - Secondary action button (gray)
.btn-success - Success action button (green)
.btn-warning - Warning action button (amber)
.btn-danger - Error action button (red)
```

### Cards
```css
.card - Base card component
.card-elevated - Card with enhanced shadow
.card-interactive - Clickable card with hover effects
.card-header - Card header section
.card-content - Card main content
.card-footer - Card footer section
```

### Form Elements
```css
.form-input - Base input field styling
.form-label - Form label styling
```

### Status Badges
```css
.badge - Base badge component
.badge-success - Success status badge
.badge-warning - Warning status badge  
.badge-error - Error status badge
.badge-info - Info status badge
.badge-neutral - Neutral status badge
```

### Navigation
```css
.nav-link - Base navigation link
.nav-link-active - Active navigation state
.nav-link-inactive - Inactive navigation state
```

## Layout System
- **Grid System**: CSS Grid and Flexbox for responsive layouts
- **Spacing**: Consistent spacing scale (4px, 8px, 16px, 24px, 32px, etc.)
- **Breakpoints**: Mobile-first responsive design
- **Container**: Centered content with max-width constraints

## Interactive States
- **Hover**: Subtle color changes and elevation
- **Focus**: Prominent focus rings for accessibility
- **Active**: Scale and shadow changes for feedback
- **Disabled**: Reduced opacity and cursor changes

## Animation System
- **Duration**: Fast (150ms), Normal (300ms), Slow (500ms)
- **Easing**: CSS cubic-bezier for natural motion
- **Keyframes**: Fade-in, slide-up, and scale-in animations
- **Reduced Motion**: Respects user preferences

## CSS Architecture
```
theme/static_src/src/styles.css
├── @tailwind base      - Tailwind base styles
├── @tailwind components - Custom component classes
├── @tailwind utilities - Utility classes
├── @layer base         - Custom base styles
├── @layer components   - Component definitions
└── @layer utilities    - Custom utilities
```

## Build Process
1. Source CSS: `theme/static_src/src/styles.css`
2. Build Command: `npm run build` (in theme/static_src)
3. Output: `theme/static/css/styles.css`
4. Django Static: Collected to `staticfiles/css/styles.css`

### Quick Build Script
```bash
./build_css.sh
```

## Alpine.js Integration
- **Local Installation**: Served from static files (not CDN)
- **Reactive Components**: Dashboard stats, navigation, notifications
- **Accessibility**: Proper ARIA attributes and keyboard support

## File Structure
```
TPS/
├── theme/static_src/          - CSS source files
│   ├── src/styles.css         - Main Tailwind CSS file
│   ├── tailwind.config.js     - Tailwind configuration
│   └── package.json           - Build dependencies
├── theme/static/css/          - Compiled CSS output
├── frontend/static/           - Additional static files
│   └── js/vendor/             - Local JavaScript libraries
└── staticfiles/               - Django collected static files
```

## Best Practices
1. **Use Semantic Classes**: Prefer `.btn-primary` over raw Tailwind utilities in templates
2. **Consistent Spacing**: Use the spacing scale (space-y-4, gap-6, etc.)
3. **Accessible Colors**: Ensure sufficient contrast for all text
4. **Responsive Design**: Test on multiple screen sizes
5. **Performance**: Keep CSS bundle size minimal

## Maintenance
- **CSS Changes**: Edit `theme/static_src/src/styles.css`
- **Build**: Run `./build_css.sh` after changes
- **Testing**: Verify across different browsers and screen sizes
- **Documentation**: Update this file when adding new components

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---
*TPS V1.4 Design System - Consistent, Accessible, Professional*