# Migration Guide: Converting Existing Pages to New Layout System

## Overview
This guide provides step-by-step instructions for converting existing TPS pages to use the new unified layout system. The goal is to maintain functionality while improving consistency and desktop optimization.

## Pre-Migration Assessment

### 1. Identify Page Types
Before migrating, categorize your existing pages:

- **Dashboard Pages**: Overview pages with stats and widgets
- **List/Table Pages**: Pages displaying tabular data
- **Form Pages**: Data input and editing pages
- **Detail Pages**: Single item detail views
- **Custom Pages**: Unique layouts requiring special handling

### 2. Current Layout Analysis
Review existing pages for:
- Container structure (`max-w-*`, padding, margins)
- Grid systems (`grid-cols-*`, `lg:grid-cols-*`)
- Header patterns (titles, descriptions, actions)
- Sidebar implementations
- Responsive behavior issues
- Custom CSS dependencies

## Migration Process

### Step 1: Backup Original
Always create a backup before migrating:

```bash
# Create backup of original template
cp frontend/templates/pages/original_page.html frontend/templates/pages/original_page_backup.html
```

### Step 2: Update Base Structure

#### Before:
```html
{% extends 'base.html' %}

{% block content %}
<div class="max-w-7xl mx-auto p-6">
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">Page Title</h1>
        <p class="text-gray-600">Page description</p>
    </div>
    
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- content -->
    </div>
</div>
{% endblock %}
```

#### After:
```html
{% extends 'base.html' %}

{% block content %}
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" %}

{% block page_content %}
    {% include 'layouts/page_header.html' with title="Page Title" description="Page description" %}
    
    {% include 'layouts/content_layout.html' with layout_type="single" %}
    
    {% block primary_content %}
        <!-- content -->
    {% endblock %}
{% endblock %}
{% endblock %}
```

### Step 3: Migrate Specific Page Types

#### Dashboard Page Migration

**Before:**
```html
<!-- Old dashboard structure -->
<div class="grid grid-cols-4 gap-6 mb-8">
    <div class="bg-blue-600 text-white p-6 rounded-lg">
        <div class="text-2xl font-bold">{{ user_count }}</div>
        <div class="text-sm opacity-90">Active Users</div>
    </div>
    <!-- more stats -->
</div>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2">
        <!-- main content -->
    </div>
    <div>
        <!-- sidebar -->
    </div>
</div>
```

**After:**
```html
<!-- New dashboard structure -->
{% include 'layouts/stats_grid.html' with stats=dashboard_stats columns="4" %}

{% include 'layouts/content_layout.html' with layout_type="sidebar-right" %}

{% block primary_content %}
    <!-- main content -->
{% endblock %}

{% block right_sidebar %}
    <!-- sidebar -->
{% endblock %}
```

**View Changes Required:**
```python
# In your view
def dashboard_view(request):
    # Convert stats to new format
    dashboard_stats = [
        {
            'title': 'Active Users',
            'value': str(user_count),
            'icon': 'users',
            'color': 'blue',
            'link': '/users/',
            'description': 'Currently online'
        },
        # ... more stats
    ]
    
    context = {
        'dashboard_stats': dashboard_stats,
        # ... other context
    }
    return render(request, 'pages/dashboard.html', context)
```

#### Table Page Migration

**Before:**
```html
<div class="bg-white shadow rounded-lg overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium">Users</h3>
    </div>
    
    <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
            <!-- table content -->
        </table>
    </div>
</div>
```

**After:**
```html
{% include 'layouts/table_layout.html' with table_id="users-table" title="Users" show_search=True %}

{% block table_head %}
    <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Status</th>
    </tr>
{% endblock %}

{% block table_body %}
    {% for user in users %}
    <tr>
        <td>{{ user.name }}</td>
        <td>{{ user.email }}</td>
        <td><span class="badge badge-success">Active</span></td>
    </tr>
    {% endfor %}
{% endblock %}
```

#### Form Page Migration

**Before:**
```html
<div class="max-w-2xl mx-auto">
    <form class="space-y-6">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
                <label class="block text-sm font-medium text-gray-700">First Name</label>
                <input type="text" class="mt-1 block w-full border-gray-300 rounded-md">
            </div>
            <!-- more fields -->
        </div>
    </form>
</div>
```

**After:**
```html
{% include 'layouts/content_layout.html' with layout_type="single" %}

{% block primary_content %}
<div class="p-6">
    <form class="space-y-6">
        <fieldset class="form-section">
            <legend class="text-lg font-semibold mb-4">Personal Information</legend>
            
            <div class="desktop-grid desktop-grid-2 gap-6">
                <div>
                    <label for="first_name" class="form-label">First Name</label>
                    <input type="text" id="first_name" class="form-input">
                </div>
                <!-- more fields -->
            </div>
        </fieldset>
    </form>
</div>
{% endblock %}
```

### Step 4: Update CSS Classes

#### Replace Custom Button Classes
```html
<!-- Before -->
<button class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
    Save
</button>

<!-- After -->
<button class="btn-primary">
    Save
</button>
```

#### Replace Card Structures
```html
<!-- Before -->
<div class="bg-white shadow rounded-lg p-6">
    <h3 class="text-lg font-semibold mb-4">Card Title</h3>
    <p>Content</p>
</div>

<!-- After -->
<div class="card">
    <div class="card-header">
        <h3 class="text-lg font-semibold">Card Title</h3>
    </div>
    <div class="card-content">
        <p>Content</p>
    </div>
</div>
```

#### Replace Form Elements
```html
<!-- Before -->
<input type="text" class="block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500">

<!-- After -->
<input type="text" class="form-input focus-ring">
```

### Step 5: Add Accessibility Features

#### Form Accessibility
```html
<!-- Before -->
<input type="text" placeholder="Enter name">

<!-- After -->
<label for="name" class="form-label">Name *</label>
<input type="text" id="name" class="form-input focus-ring" required aria-describedby="name-help">
<p id="name-help" class="text-sm text-gray-500 mt-1">Enter your full name</p>
```

#### Focus Management
```html
<!-- Add focus-ring class to interactive elements -->
<button class="btn-primary focus-ring">Action</button>
<a href="#" class="text-blue-600 hover:text-blue-800 focus-ring">Link</a>
```

### Step 6: Test Responsive Behavior

#### Desktop Testing (1024px+)
- Verify layout utilizes full screen width effectively
- Check sidebar placement and sizing
- Ensure adequate information density
- Test keyboard navigation

#### Tablet Testing (768px - 1024px)
- Confirm layout adapts appropriately
- Check that sidebars stack or hide as needed
- Verify touch targets are adequate size

#### Mobile Testing (< 768px)
- Ensure content stacks vertically
- Check that all functionality remains accessible
- Verify text remains readable
- Test form usability

## Common Migration Patterns

### Pattern 1: Stats Grid Conversion
```python
# Convert individual stat cards to stats array
def convert_stats(old_stats):
    return [
        {
            'title': stat['title'],
            'value': str(stat['value']),
            'icon': stat['icon_name'],  # Map to standard icons
            'color': 'blue',  # Choose appropriate color
            'link': stat.get('link_url'),
            'description': stat.get('subtitle')
        }
        for stat in old_stats
    ]
```

### Pattern 2: Sidebar Content Organization
```html
<!-- Organize sidebar content into sections -->
{% block right_sidebar %}
<div class="space-y-6">
    <!-- Section 1 -->
    <div>
        <h4 class="text-sm font-medium text-gray-900 mb-3">Quick Actions</h4>
        <!-- actions -->
    </div>
    
    <!-- Section 2 -->
    <div>
        <h4 class="text-sm font-medium text-gray-900 mb-3">Recent Activity</h4>
        <!-- activity -->
    </div>
</div>
{% endblock %}
```

### Pattern 3: Complex Grid Layouts
```html
<!-- Before: Complex CSS Grid -->
<div class="grid grid-cols-12 gap-6">
    <div class="col-span-8"><!-- main --></div>
    <div class="col-span-4"><!-- side --></div>
</div>

<!-- After: Semantic Layout -->
{% include 'layouts/content_layout.html' with layout_type="sidebar-right" sidebar_width="standard" %}
```

## Troubleshooting Common Issues

### Issue: Layout Breaks on Mobile
**Cause**: Desktop-specific CSS overriding mobile layout
**Solution**: Remove custom grid classes, use layout components

```html
<!-- Remove -->
<div class="hidden lg:block lg:col-span-3">

<!-- Replace with -->
{% block right_sidebar %}
    <!-- Content automatically handles responsive behavior -->
{% endblock %}
```

### Issue: Buttons Not Styled
**Cause**: Missing component classes
**Solution**: Replace utility classes with component classes

```html
<!-- Replace utility combinations -->
<button class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">

<!-- With component class -->
<button class="btn-primary focus-ring">
```

### Issue: Forms Not Accessible
**Cause**: Missing labels and ARIA attributes
**Solution**: Add proper form structure

```html
<!-- Add proper labeling -->
<div>
    <label for="email" class="form-label">Email Address *</label>
    <input type="email" id="email" class="form-input focus-ring" required>
</div>
```

### Issue: Inconsistent Spacing
**Cause**: Mixed use of spacing utilities
**Solution**: Use consistent spacing scale

```html
<!-- Use consistent spacing -->
<div class="space-y-6">  <!-- Instead of various mb-* classes -->
    <section class="form-section">  <!-- Standard section spacing -->
        <!-- content -->
    </section>
</div>
```

## Testing Checklist

### Visual Testing
- [ ] Page renders correctly on desktop (1024px+)
- [ ] Layout adapts properly on tablet (768-1024px)
- [ ] Content stacks appropriately on mobile (<768px)
- [ ] Colors and typography are consistent
- [ ] Spacing follows design system

### Functionality Testing
- [ ] All interactive elements work
- [ ] Forms submit properly
- [ ] Navigation remains functional
- [ ] Search and filters operate correctly
- [ ] Modal and dropdown behavior unchanged

### Accessibility Testing
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility maintained
- [ ] Focus indicators visible
- [ ] Color contrast meets standards
- [ ] Error messages properly associated

### Performance Testing
- [ ] Page loads quickly
- [ ] No layout shifts during load
- [ ] Animations perform smoothly
- [ ] No console errors

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Restore from backup file
```bash
cp frontend/templates/pages/original_page_backup.html frontend/templates/pages/original_page.html
```

2. **Partial Rollback**: Revert specific sections while keeping others
3. **CSS Fallback**: Add temporary CSS overrides if needed
4. **Feature Flag**: Use conditional logic to switch between old/new layouts

## Post-Migration Tasks

### 1. Clean Up
- Remove unused CSS classes
- Delete backup files after testing
- Update any custom JavaScript that references old classes

### 2. Documentation
- Update component documentation
- Add page-specific notes for future developers
- Document any custom modifications made

### 3. Monitoring
- Monitor for user feedback
- Check analytics for usability issues
- Address any reported problems quickly

### 4. Optimization
- Review page performance
- Optimize images and assets
- Consider lazy loading for heavy content

## Best Practices for Future Pages

1. **Start with Layout System**: Always begin new pages using layout components
2. **Follow Component Patterns**: Use established component classes
3. **Test Responsive Early**: Check multiple screen sizes during development
4. **Validate Accessibility**: Include accessibility testing in review process
5. **Document Decisions**: Record any custom modifications and reasoning

This migration guide should be updated as new patterns emerge and lessons are learned from the migration process.