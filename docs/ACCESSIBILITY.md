# TPS Accessibility Guide

## Overview
This guide documents the accessibility improvements implemented in the TPS Team Planning System to ensure WCAG 2.1 AA compliance.

## Implemented Accessibility Features

### 1. Semantic HTML Structure
- **Landmarks**: Proper use of `<main>`, `<aside>`, `<header>`, `<section>`, and `<article>` elements
- **Headings**: Logical hierarchy from h1-h6
- **Forms**: Proper `<fieldset>` and `<legend>` usage for form groupings
- **Lists**: Semantic lists for navigation and content organization

### 2. ARIA Labels and Descriptions
- **Navigation**: `role="navigation"` with `aria-label` for main navigation
- **Buttons**: `aria-label` for icon-only buttons with descriptive text
- **Forms**: `aria-describedby` linking form fields to help text and errors
- **Live Regions**: `aria-live="polite"` for notifications and dynamic content
- **Alerts**: `role="alert"` for error messages and important notifications

### 3. Keyboard Navigation
- **Skip Links**: "Skip to main content" for keyboard users
- **Focus Management**: Proper focus indicators and logical tab order
- **Interactive Elements**: All clickable elements are keyboard accessible
- **Dropdowns**: Arrow key navigation for dropdown menus
- **Modals**: Focus trapping when modal dialogs are open

### 4. Color and Contrast
- **High Contrast**: All text meets WCAG AA contrast ratios (4.5:1 minimum)
- **Color Independence**: Information not conveyed by color alone
- **Status Indicators**: Icons and text used together for status communication
- **Dark Mode**: Proper contrast maintained in both light and dark themes

### 5. Form Accessibility
- **Labels**: All form inputs have proper labels
- **Required Fields**: Clear indication with `aria-required="true"`
- **Error Handling**: Real-time validation with screen reader announcements
- **Help Text**: Descriptive help text linked via `aria-describedby`
- **Field Groups**: Related fields grouped with `<fieldset>` and `<legend>`

### 6. Dynamic Content
- **Live Regions**: Status updates announced to screen readers
- **Loading States**: Clear indication when content is loading
- **Error Messages**: Immediate feedback for user actions
- **Progressive Enhancement**: Core functionality works without JavaScript

## WCAG 2.1 Compliance Checklist

### Level A Requirements ✅
- [x] Images have alt text or are marked as decorative
- [x] Form controls have labels
- [x] Page has a main heading
- [x] Headings are in logical order
- [x] Links have descriptive text
- [x] Page content is keyboard accessible

### Level AA Requirements ✅
- [x] Color contrast meets 4.5:1 ratio for normal text
- [x] Color contrast meets 3:1 ratio for large text
- [x] Text can be resized up to 200% without loss of functionality
- [x] All functionality is keyboard accessible
- [x] Focus indicators are visible
- [x] Page has a descriptive title
- [x] Headings and labels are descriptive
- [x] Error identification and suggestions provided

## Testing Recommendations

### Keyboard Testing
1. Use Tab to navigate through all interactive elements
2. Use Shift+Tab to navigate backwards
3. Use Enter/Space to activate buttons and links
4. Use arrow keys in dropdown menus
5. Ensure all functionality is accessible without a mouse

### Screen Reader Testing
1. Test with NVDA (Windows), JAWS (Windows), or VoiceOver (Mac)
2. Verify all content is announced properly
3. Check that form labels and errors are read correctly
4. Ensure navigation landmarks are properly identified
5. Test that dynamic content updates are announced

### Automated Testing Tools
- **axe-core**: For automated accessibility scanning
- **WAVE**: Web accessibility evaluation tool
- **Lighthouse**: Google's accessibility audit
- **Pa11y**: Command-line accessibility testing

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Internet Explorer 11 (basic support)

## Implementation Details

### CSS Custom Properties
```css
:root {
  --color-primary: 59 130 246;
  --focus-ring: 0 0 0 2px rgb(var(--color-primary));
}
```

### Focus Management
```javascript
// Focus trapping in modals
const trapFocus = (element) => {
  const focusableElements = element.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  // Implementation details in base.js
};
```

### ARIA Live Regions
```html
<div role="region" aria-label="Notifications" aria-live="polite">
  <!-- Dynamic notifications -->
</div>
```

## Future Improvements
- [ ] High contrast mode support
- [ ] Reduced motion preferences
- [ ] Voice control compatibility
- [ ] Enhanced touch target sizes (44px minimum)
- [ ] Better support for assistive technologies

## Resources
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [WebAIM](https://webaim.org/)
- [A11y Project](https://www.a11yproject.com/)