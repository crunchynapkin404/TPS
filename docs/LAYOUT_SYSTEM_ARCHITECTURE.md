# TPS Page Layout System Architecture

## Overview
This document defines the unified layout system architecture for the TPS V1.4 Team Planning System, addressing inconsistent page layouts and providing a desktop-first responsive framework.

## Design Principles

### 1. Desktop-First Approach
- Optimize for desktop screens (1024px+) with responsive mobile adaptations
- Maximize screen real estate utilization
- Prioritize information density and workflow efficiency

### 2. Component Hierarchy
- Reusable layout components for consistent page structure
- Composable sections that can be mixed and matched
- Clear separation of layout concerns from content

### 3. Progressive Enhancement
- Core layout works without JavaScript
- Enhanced interactions with Alpine.js
- Graceful degradation for mobile devices

## Layout Component Hierarchy

```
Base Layout (base.html)
├── Sidebar Navigation (existing)
├── Main Content Area
    ├── Page Layout Wrapper
        ├── Page Header Component
        ├── Content Layout Component
        │   ├── Primary Content Area
        │   ├── Secondary Sidebar (optional)
        │   └── Action Panel (optional)
        └── Page Footer Component (optional)
```

## Core Layout Components

### 1. Page Layout Wrapper (`page-wrapper`)
**Purpose**: Standardizes page structure and responsive behavior
**Classes**: `.page-wrapper`, `.page-wrapper-fluid`, `.page-wrapper-contained`

```html
<!-- Standard contained layout -->
<div class="page-wrapper">
  <!-- Page content -->
</div>

<!-- Full-width layout -->
<div class="page-wrapper-fluid">
  <!-- Full-width content -->
</div>

<!-- Custom contained layout -->
<div class="page-wrapper-contained">
  <!-- Contained content with max-width -->
</div>
```

### 2. Page Header Component (`page-header`)
**Purpose**: Consistent page titles, breadcrumbs, and primary actions
**Variants**: Standard, compact, with-actions, with-tabs

```html
<div class="page-header">
  <div class="page-header-content">
    <div class="page-header-text">
      <h1 class="page-title">Page Title</h1>
      <p class="page-description">Optional description</p>
    </div>
    <div class="page-header-actions">
      <!-- Primary actions -->
    </div>
  </div>
</div>
```

### 3. Content Layout Component (`content-layout`)
**Purpose**: Flexible content area with optional sidebars
**Variants**: Single column, sidebar-left, sidebar-right, two-sidebar

```html
<!-- Single column layout -->
<div class="content-layout">
  <main class="content-primary">
    <!-- Main content -->
  </main>
</div>

<!-- Layout with right sidebar -->
<div class="content-layout content-layout-sidebar-right">
  <main class="content-primary">
    <!-- Main content -->
  </main>
  <aside class="content-sidebar">
    <!-- Secondary content -->
  </aside>
</div>
```

### 4. Stats Grid Component (`stats-grid`)
**Purpose**: Consistent dashboard statistics display
**Responsive**: 1-6 columns based on screen size

```html
<div class="stats-grid">
  <div class="stat-card stat-card-primary">
    <!-- Stat content -->
  </div>
  <!-- More stat cards -->
</div>
```

### 5. Data Table Layout (`table-layout`)
**Purpose**: Optimized table display with filters and actions
**Features**: Sticky headers, responsive overflow, filter panel

```html
<div class="table-layout">
  <div class="table-header">
    <div class="table-filters"><!-- Filters --></div>
    <div class="table-actions"><!-- Actions --></div>
  </div>
  <div class="table-container">
    <!-- Table content -->
  </div>
</div>
```

## Responsive Breakpoints

### Desktop-First Media Queries
```css
/* Ultra-wide desktops (1920px+) */
@media (min-width: 120rem) { /* 1920px */ }

/* Wide desktops (1440px+) */
@media (min-width: 90rem) { /* 1440px */ }

/* Standard desktops (1024px+) */
@media (min-width: 64rem) { /* 1024px */ }

/* Tablets (768px+) */
@media (min-width: 48rem) { /* 768px */ }

/* Mobile (default) */
@media (max-width: 47.9375rem) { /* < 768px */ }
```

### Grid System
```css
.desktop-grid-1 { grid-template-columns: 1fr; }
.desktop-grid-2 { grid-template-columns: repeat(2, 1fr); }
.desktop-grid-3 { grid-template-columns: repeat(3, 1fr); }
.desktop-grid-4 { grid-template-columns: repeat(4, 1fr); }
.desktop-grid-6 { grid-template-columns: repeat(6, 1fr); }

/* Responsive variations */
.grid-responsive-stats {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr; /* Mobile: single column */
}

@media (min-width: 48rem) {
  .grid-responsive-stats {
    grid-template-columns: repeat(2, 1fr); /* Tablet: 2 columns */
  }
}

@media (min-width: 64rem) {
  .grid-responsive-stats {
    grid-template-columns: repeat(4, 1fr); /* Desktop: 4 columns */
  }
}

@media (min-width: 90rem) {
  .grid-responsive-stats {
    grid-template-columns: repeat(6, 1fr); /* Wide: 6 columns */
  }
}
```

## Content Patterns

### 1. Dashboard Layout
- Full-width header with welcome message
- Stats grid (4-6 columns on desktop)
- Content area with cards/widgets
- Action panels on the right

### 2. List/Table Layout
- Compact header with filters
- Full-width table with sticky headers
- Right sidebar for details (optional)
- Bottom pagination

### 3. Form Layout
- Centered form with max-width
- Side-by-side fields on desktop
- Progress indicators for multi-step
- Action bar at bottom

### 4. Detail/Profile Layout
- Left sidebar with navigation
- Main content area with sections
- Right sidebar for metadata
- Fixed action buttons

## Error Handling & Edge Cases

### Content Overflow
- Implement horizontal scroll for wide tables
- Text truncation with tooltips for long content
- Responsive image scaling

### Empty States
- Consistent empty state components
- Clear call-to-action messages
- Helpful onboarding hints

### Loading States
- Skeleton loaders for content areas
- Progressive loading for large datasets
- Graceful fallbacks for JavaScript failures

## Z-Index Management

```css
/* Z-index scale for layered elements */
.z-index-dropdown: 10;
.z-index-sticky: 20;
.z-index-header: 30;
.z-index-sidebar: 40;
.z-index-modal-backdrop: 50;
.z-index-modal: 60;
.z-index-popover: 70;
.z-index-tooltip: 80;
.z-index-notification: 90;
.z-index-debug: 100;
```

## Performance Considerations

### CSS Optimization
- Minimal custom CSS, leverage Tailwind utilities
- Component-scoped styles when needed
- Avoid complex selectors and deep nesting

### Layout Shifts
- Reserve space for dynamic content
- Use aspect-ratio for media elements
- Consistent grid sizing

### Accessibility
- Semantic HTML structure
- Proper heading hierarchy
- Focus management for dynamic content
- ARIA landmarks for layout regions

## Implementation Timeline

1. **Phase 1**: Core layout components (page wrapper, header, content layout)
2. **Phase 2**: Specialized components (stats grid, table layout)
3. **Phase 3**: Advanced patterns (detail layouts, form layouts)
4. **Phase 4**: Migration of existing pages
5. **Phase 5**: Documentation and style guide

## Next Steps

1. Create template components in `frontend/templates/layouts/`
2. Implement CSS classes in `theme/static_src/src/styles.css`
3. Build sample pages demonstrating each layout pattern
4. Create migration guide for existing pages
5. Document component API and usage examples