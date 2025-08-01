# TPS Component Library

## Overview
This document outlines the standardized components and design patterns used in the TPS Team Planning System.

## Design System

### Color Palette
```css
/* Primary Colors */
--color-primary: 59 130 246;     /* Blue-500 */
--color-primary-dark: 37 99 235; /* Blue-600 */

/* Semantic Colors */
--color-success: 16 185 129;     /* Emerald-500 */
--color-warning: 245 158 11;     /* Amber-500 */
--color-error: 239 68 68;        /* Red-500 */
--color-info: 59 130 246;        /* Blue-500 */
```

### Typography Scale
- **XS**: 0.75rem (12px)
- **SM**: 0.875rem (14px)
- **Base**: 1rem (16px)
- **LG**: 1.125rem (18px)
- **XL**: 1.25rem (20px)

### Spacing Scale
- **XS**: 0.25rem (4px)
- **SM**: 0.5rem (8px)
- **MD**: 1rem (16px)
- **LG**: 1.5rem (24px)
- **XL**: 2rem (32px)

## Components

### Buttons

#### Primary Button
```html
<button class="btn-primary">
  <svg class="w-4 h-4 mr-2" aria-hidden="true"><!-- icon --></svg>
  Primary Action
</button>
```

#### Secondary Button
```html
<button class="btn-secondary">
  Secondary Action
</button>
```

#### Button Variants
- `btn-primary` - Main call-to-action
- `btn-secondary` - Secondary actions
- `btn-success` - Positive actions (save, approve)
- `btn-warning` - Caution actions
- `btn-danger` - Destructive actions (delete)

### Form Components

#### Input Field
```html
<div class="field-group">
  <label for="input-id" class="form-label">
    Field Label <span class="text-red-500" aria-label="required">*</span>
  </label>
  <input id="input-id" 
         class="form-input" 
         type="text"
         aria-describedby="input-help input-error"
         aria-required="true">
  <p id="input-help" class="text-sm text-gray-500 mt-1">Help text</p>
  <p id="input-error" class="text-sm text-red-600 mt-1 hidden" role="alert">Error message</p>
</div>
```

#### Form Section
```html
<fieldset class="form-section">
  <legend class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
    Section Title
  </legend>
  <!-- Form fields -->
</fieldset>
```

### Cards

#### Basic Card
```html
<div class="card">
  <div class="card-header">
    <h3 class="text-lg font-semibold">Card Title</h3>
  </div>
  <div class="card-body">
    <p>Card content</p>
  </div>
  <div class="card-footer">
    <button class="btn-primary">Action</button>
  </div>
</div>
```

#### Dashboard Stat Card
```html
<article class="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-5 rounded-lg flex flex-col items-center justify-center text-center relative overflow-hidden cursor-pointer transition-all duration-200 shadow-lg shadow-blue-500/30 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/40 focus-within:ring-2 focus-within:ring-blue-300" 
         role="button"
         tabindex="0"
         aria-label="View details: 5 items"
         @click="navigate()"
         @keydown.enter="navigate()"
         @keydown.space.prevent="navigate()">
  <div class="text-2xl mb-2 opacity-90" aria-hidden="true">
    <svg class="w-8 h-8"><!-- icon --></svg>
  </div>
  <div class="text-3xl font-bold mb-1">5</div>
  <div class="text-sm opacity-90 font-medium">Items</div>
</article>
```

### Navigation

#### Sidebar Navigation
```html
<aside class="..." role="navigation" aria-label="Main navigation">
  <nav>
    <ul>
      <li>
        <a href="/dashboard" 
           class="flex items-center px-4 py-2 text-sm font-medium rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
           aria-current="page">
          <svg class="w-5 h-5 mr-3" aria-hidden="true"><!-- icon --></svg>
          Dashboard
        </a>
      </li>
    </ul>
  </nav>
</aside>
```

### Notifications

#### Notification Toast
```html
<div class="px-4 py-2 rounded-lg shadow-lg transform transition-all duration-300 flex items-center gap-2 text-white max-w-sm bg-green-500"
     role="alert"
     aria-live="polite"
     aria-label="Success: Action completed">
  <span aria-hidden="true">✅</span>
  <span>Action completed successfully!</span>
  <button class="ml-2 text-white hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 rounded"
          aria-label="Close notification">
    <svg class="w-4 h-4" aria-hidden="true"><!-- close icon --></svg>
  </button>
</div>
```

### Status Indicators

#### Status Dot
```html
<span class="status-dot status-online" aria-label="Online"></span>
```

Status variants:
- `status-online` - Green dot
- `status-offline` - Gray dot  
- `status-busy` - Yellow dot
- `status-error` - Red dot

### Loading States

#### Button Loading
```html
<button class="btn-primary" disabled>
  <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" aria-hidden="true">
    <!-- spinner icon -->
  </svg>
  Loading...
</button>
```

#### Content Loading
```html
<div class="loading">
  <div class="animate-pulse">
    <div class="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
    <div class="h-4 bg-gray-300 rounded w-1/2"></div>
  </div>
</div>
```

## Accessibility Guidelines

### General Rules
1. All interactive elements must be keyboard accessible
2. Use semantic HTML elements when available
3. Provide alternative text for images
4. Use ARIA labels for screen readers
5. Maintain proper color contrast (4.5:1 minimum)
6. Group related form fields with fieldsets

### Focus Management
```css
*:focus {
  outline: 2px solid rgb(var(--color-primary));
  outline-offset: 2px;
}
```

### Screen Reader Support
- Use `aria-label` for buttons without text
- Use `aria-describedby` to link help text
- Use `role="alert"` for error messages
- Use `aria-live` for dynamic content
- Hide decorative elements with `aria-hidden="true"`

## JavaScript Patterns

### Alpine.js Components
```javascript
// Component data function
function componentData() {
  return {
    // Reactive data
    items: [],
    loading: false,
    
    // Methods
    async loadData() {
      this.loading = true;
      try {
        this.items = await window.TPS.utils.apiCall('/api/data');
      } finally {
        this.loading = false;
      }
    },
    
    // Lifecycle
    init() {
      this.loadData();
    }
  }
}
```

### API Calls
```javascript
// Use the utility function for consistent error handling
const data = await window.TPS.utils.apiCall('/api/endpoint', {
  method: 'POST',
  body: JSON.stringify({ data: 'value' })
});
```

### Notifications
```javascript
// Dispatch notification
this.$dispatch('show-notification', {
  message: 'Action completed!',
  type: 'success' // 'success', 'error', 'warning', 'info'
});
```

## Testing

### Component Testing
1. Test keyboard navigation
2. Test with screen readers
3. Verify color contrast
4. Test responsive behavior
5. Validate HTML semantics

### Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Internet Explorer 11 (graceful degradation)

## Migration Guide

### From Old Patterns
```html
<!-- Before -->
<div class="bg-blue-600 text-white px-4 py-2 rounded">Button</div>

<!-- After -->
<button class="btn-primary">Button</button>
```

### CSS Class Updates
- Replace `text-blue-600` with `text-primary`
- Replace `bg-blue-600` with `bg-primary`
- Use semantic button classes instead of utility combinations