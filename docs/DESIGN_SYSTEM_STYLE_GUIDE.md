# TPS Design System Style Guide

## Overview
This style guide defines the visual design standards for the TPS Team Planning System, focusing on desktop-first responsive design with consistent components and patterns.

## Design Principles

### 1. Desktop-First Approach
- Optimize layouts for desktop screens (1024px+)
- Progressive enhancement for smaller screens
- Maximize information density and workflow efficiency

### 2. Consistency
- Use standardized components and patterns
- Maintain consistent spacing, colors, and typography
- Follow established interaction patterns

### 3. Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Sufficient color contrast ratios

### 4. Performance
- Minimal custom CSS
- Leverage Tailwind utility classes
- Optimize for fast rendering

## Visual Foundation

### Typography

#### Font Family
```css
font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
```

#### Type Scale
```css
/* Headings */
.text-4xl  /* 36px - Page titles */
.text-3xl  /* 30px - Section titles */  
.text-2xl  /* 24px - Subsection titles */
.text-xl   /* 20px - Card titles */
.text-lg   /* 18px - Component titles */

/* Body Text */
.text-base /* 16px - Primary body text */
.text-sm   /* 14px - Secondary text */
.text-xs   /* 12px - Helper text, captions */
```

#### Usage Guidelines
- **Page Titles**: Use `text-3xl` or `text-4xl` with `font-bold`
- **Section Headings**: Use `text-2xl` with `font-semibold`
- **Body Text**: Use `text-base` for readability
- **Secondary Text**: Use `text-sm` with gray color
- **Line Height**: Default 1.6 for body text, 1.2 for headings

### Color Palette

#### Primary Colors
```css
/* Blue - Primary brand color */
--color-primary: 59 130 246;      /* blue-500 */
--color-primary-dark: 37 99 235;  /* blue-600 */
--color-primary-light: 147 197 253; /* blue-300 */
```

#### Semantic Colors
```css
/* Success - Green */
--color-success: 16 185 129;      /* emerald-500 */

/* Warning - Amber */  
--color-warning: 245 158 11;      /* amber-500 */

/* Error - Red */
--color-error: 239 68 68;         /* red-500 */

/* Info - Blue */
--color-info: 59 130 246;         /* blue-500 */

/* Neutral - Gray */
--color-neutral: 107 114 128;     /* gray-500 */
```

#### Usage Guidelines
- **Primary Actions**: Use blue for main CTAs and navigation
- **Success States**: Use green for confirmations and positive feedback
- **Warnings**: Use amber for caution states and pending actions
- **Errors**: Use red for errors and destructive actions
- **Information**: Use blue for informational messages
- **Neutral**: Use gray for secondary elements and disabled states

### Spacing System

#### Scale
```css
--spacing-xs: 0.25rem;  /* 4px */
--spacing-sm: 0.5rem;   /* 8px */
--spacing-md: 1rem;     /* 16px */
--spacing-lg: 1.5rem;   /* 24px */
--spacing-xl: 2rem;     /* 32px */
--spacing-2xl: 2.5rem;  /* 40px */
--spacing-3xl: 3rem;    /* 48px */
--spacing-4xl: 4rem;    /* 64px */
```

#### Usage Guidelines
- **Component Padding**: Use `p-4` (16px) or `p-6` (24px)
- **Section Spacing**: Use `space-y-6` (24px) or `space-y-8` (32px)
- **Grid Gaps**: Use `gap-4` (16px) to `gap-6` (24px)
- **Page Margins**: Use `mx-auto` with max-width containers

### Border Radius
```css
--radius-xs: 0.125rem; /* 2px */
--radius-sm: 0.25rem;  /* 4px */
--radius-md: 0.375rem; /* 6px */
--radius-lg: 0.5rem;   /* 8px */
--radius-xl: 0.75rem;  /* 12px */
--radius-2xl: 1rem;    /* 16px */
```

### Shadows
```css
/* Elevation levels */
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1);        /* Cards */
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);      /* Elevated cards */
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);    /* Modals */
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);    /* Dropdowns */
```

## Component Standards

### Buttons

#### Primary Button
```html
<button class="btn-primary">
    Primary Action
</button>
```

**Visual Properties:**
- Background: `bg-blue-600`
- Text: `text-white`
- Padding: `px-4 py-2`
- Border Radius: `rounded-md`
- Font Weight: `font-medium`

#### Secondary Button
```html
<button class="btn-secondary">
    Secondary Action  
</button>
```

**Visual Properties:**
- Background: `bg-white`
- Text: `text-gray-700`
- Border: `border border-gray-300`
- Padding: `px-4 py-2`

#### Button Sizes
```html
<button class="btn-primary btn-sm">Small</button>
<button class="btn-primary">Default</button>
<button class="btn-primary btn-lg">Large</button>
```

#### Button States
- **Default**: Normal appearance
- **Hover**: Darker background, slight elevation
- **Focus**: Blue focus ring with 2px offset
- **Active**: Slight scale down (transform: scale(0.98))
- **Disabled**: 50% opacity, cursor not-allowed

### Cards

#### Basic Card
```html
<div class="card">
    <div class="card-header">
        <h3>Card Title</h3>
    </div>
    <div class="card-content">
        <p>Card content goes here</p>
    </div>
    <div class="card-footer">
        <button class="btn-primary">Action</button>
    </div>
</div>
```

**Visual Properties:**
- Background: `bg-white`
- Border: `border border-gray-200`
- Border Radius: `rounded-lg`
- Shadow: `shadow-sm`

#### Interactive Card
```html
<div class="card card-interactive">
    <!-- Card content -->
</div>
```

**Interaction States:**
- **Hover**: Elevated shadow, slight lift
- **Focus**: Blue focus ring (when clickable)

### Form Elements

#### Input Fields
```html
<div>
    <label for="input" class="form-label">Field Label</label>
    <input type="text" id="input" class="form-input" placeholder="Enter text">
</div>
```

**Visual Properties:**
- Border: `border border-gray-300`
- Border Radius: `rounded-md`
- Padding: `px-3 py-2`
- Focus: Blue border and ring

#### Form Sections
```html
<fieldset class="form-section">
    <legend class="text-lg font-semibold mb-4">Section Title</legend>
    <!-- Form fields -->
</fieldset>
```

### Status Indicators

#### Badges
```html
<span class="badge badge-success">Active</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Error</span>
```

**Color Mapping:**
- **Success**: Green background with dark green text
- **Warning**: Amber background with dark amber text
- **Error**: Red background with dark red text
- **Info**: Blue background with dark blue text
- **Neutral**: Gray background with dark gray text

### Data Display

#### Stats Cards
```html
<div class="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-lg">
    <div class="text-3xl font-bold">1,234</div>
    <div class="text-sm opacity-90">Active Users</div>
</div>
```

**Gradient Colors:**
- **Blue**: `from-blue-500 to-blue-600`
- **Green**: `from-emerald-500 to-emerald-600`
- **Amber**: `from-amber-500 to-amber-600`
- **Red**: `from-red-500 to-red-600`
- **Purple**: `from-purple-500 to-purple-600`

#### Tables
```html
<table class="data-table">
    <thead>
        <tr>
            <th>Column Header</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Table data</td>
        </tr>
    </tbody>
</table>
```

**Visual Properties:**
- Header Background: `bg-gray-50`
- Row Borders: `border-b border-gray-200`
- Hover: `hover:bg-gray-50`
- Padding: `px-4 py-3` (compact: `px-3 py-2`)

## Layout Patterns

### Page Structure
```
┌─────────────────────────────────────┐
│ Page Header                         │
├─────────────────────────────────────┤
│ Content Area                        │
│ ┌─────────────────┬─────────────────┐│
│ │ Primary Content │ Sidebar (opt.)  ││
│ │                 │                 ││
│ │                 │                 ││
│ └─────────────────┴─────────────────┘│
└─────────────────────────────────────┘
```

### Grid System
```css
/* Desktop-first grid */
.desktop-grid-1  { grid-template-columns: 1fr; }
.desktop-grid-2  { grid-template-columns: repeat(2, 1fr); }
.desktop-grid-3  { grid-template-columns: repeat(3, 1fr); }
.desktop-grid-4  { grid-template-columns: repeat(4, 1fr); }
.desktop-grid-6  { grid-template-columns: repeat(6, 1fr); }
```

### Responsive Behavior
```css
/* Mobile: Stack everything */
@media (max-width: 768px) {
    .desktop-grid-* {
        grid-template-columns: 1fr;
    }
}

/* Tablet: Reduce columns */
@media (min-width: 768px) and (max-width: 1024px) {
    .desktop-grid-4, .desktop-grid-6 {
        grid-template-columns: repeat(2, 1fr);
    }
}
```

## Interaction Patterns

### Hover Effects
- **Buttons**: Background color change + subtle elevation
- **Cards**: Shadow increase + slight lift (2px)
- **Links**: Color change + underline (when appropriate)
- **Interactive elements**: Smooth transitions (200ms)

### Focus Management
- **Visible Focus Ring**: 2px blue outline with 2px offset
- **Keyboard Navigation**: Logical tab order
- **Skip Links**: Hidden until focused
- **Modal Focus Trap**: Focus stays within modal

### Loading States
```html
<!-- Button loading -->
<button class="btn-primary" disabled>
    <svg class="animate-spin w-4 h-4 mr-2">...</svg>
    Loading...
</button>

<!-- Content loading -->
<div class="animate-pulse">
    <div class="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
    <div class="h-4 bg-gray-300 rounded w-1/2"></div>
</div>
```

### Error States
```html
<!-- Form error -->
<input class="form-input border-red-500">
<p class="text-sm text-red-600 mt-1" role="alert">Error message</p>

<!-- Page error -->
<div class="text-center py-12">
    <svg class="w-12 h-12 text-gray-400 mx-auto mb-4">...</svg>
    <h3 class="text-lg font-medium text-gray-900">Something went wrong</h3>
    <p class="text-gray-500">Please try again later</p>
</div>
```

## Content Guidelines

### Writing Style
- **Tone**: Professional, clear, helpful
- **Voice**: Active voice preferred
- **Length**: Concise but informative
- **Technical Terms**: Explain when necessary

### Labels and Messages
- **Button Labels**: Action-oriented (Save, Delete, Cancel)
- **Form Labels**: Clear and descriptive
- **Error Messages**: Specific and actionable
- **Success Messages**: Confirming and encouraging

### Iconography
- **Style**: Outline icons preferred (Heroicons)
- **Size**: 16px (w-4 h-4) for inline, 24px (w-6 h-6) for buttons
- **Color**: Match text color or use semantic colors
- **Usage**: Support text, don't replace it

## Accessibility Standards

### Color and Contrast
- **Text on White**: Minimum 4.5:1 contrast ratio
- **Large Text**: Minimum 3:1 contrast ratio
- **Interactive Elements**: 3:1 contrast for focus indicators
- **Color Blind**: Don't rely solely on color for meaning

### Keyboard Navigation
- **Tab Order**: Logical and predictable
- **Focus Indicators**: Visible and high contrast
- **Keyboard Shortcuts**: Standard conventions (Esc, Enter, Space)
- **Skip Links**: Provide for main content

### Screen Readers
- **Semantic HTML**: Use proper headings, lists, tables
- **ARIA Labels**: For custom components
- **Alt Text**: Descriptive for images
- **Live Regions**: For dynamic content updates

### Form Accessibility
- **Labels**: Associated with inputs
- **Required Fields**: Clearly marked
- **Error Messages**: Linked to fields via aria-describedby
- **Field Groups**: Use fieldset and legend

## Dark Mode Support

### Color Adaptations
```css
/* Light mode (default) */
.bg-white { background-color: white; }
.text-gray-900 { color: #111827; }

/* Dark mode */
.dark .bg-white { background-color: #1f2937; }
.dark .text-gray-900 { color: white; }
```

### Component Variations
- **Cards**: `bg-white dark:bg-gray-800`
- **Text**: `text-gray-900 dark:text-white`
- **Borders**: `border-gray-200 dark:border-gray-700`
- **Inputs**: `bg-white dark:bg-gray-800`

## Performance Guidelines

### CSS Optimization
- Use Tailwind utilities over custom CSS
- Minimize large CSS files
- Leverage component classes for consistency
- Remove unused CSS in production

### Image Guidelines
- Use appropriate formats (WebP, AVIF)
- Provide proper alt text
- Use responsive images with srcset
- Lazy load images below the fold

### Animation Performance
- Prefer transform and opacity for animations
- Use CSS animations over JavaScript when possible
- Respect prefers-reduced-motion
- Keep animations under 300ms for UI feedback

## Quality Checklist

### Design Review
- [ ] Follows established component patterns
- [ ] Uses consistent spacing and typography
- [ ] Maintains visual hierarchy
- [ ] Works across different screen sizes

### Accessibility Review
- [ ] Keyboard navigation works properly
- [ ] Focus indicators are visible
- [ ] Color contrast meets standards
- [ ] Screen reader friendly

### Performance Review
- [ ] Fast loading times
- [ ] Smooth animations
- [ ] Optimized images
- [ ] Minimal custom CSS

### Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

This style guide should be updated as the design system evolves and new patterns are established.