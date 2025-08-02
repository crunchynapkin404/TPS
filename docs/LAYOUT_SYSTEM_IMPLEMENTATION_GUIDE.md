# TPS Layout System Implementation Guide

## Overview
This guide provides step-by-step instructions for implementing pages using the new TPS Layout System. The system provides consistent, desktop-first responsive layouts with reusable components.

## Quick Start

### 1. Basic Page Structure
Every page should follow this basic structure:

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<!-- Use the page wrapper -->
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" %}

{% block page_content %}
    <!-- Your page content goes here -->
{% endblock %}
{% endblock %}
```

### 2. Adding a Page Header
```html
{% include 'layouts/page_header.html' with title="Your Page Title" description="Optional description" show_actions=True %}

{% block page_actions %}
    <!-- Action buttons go here -->
    <button class="btn-primary">Primary Action</button>
    <button class="btn-secondary">Secondary Action</button>
{% endblock %}
```

### 3. Using Content Layouts
```html
<!-- Single column layout -->
{% include 'layouts/content_layout.html' with layout_type="single" %}

{% block primary_content %}
    <!-- Main content -->
{% endblock %}

<!-- Layout with sidebar -->
{% include 'layouts/content_layout.html' with layout_type="sidebar-right" sidebar_width="standard" %}

{% block primary_content %}
    <!-- Main content -->
{% endblock %}

{% block right_sidebar %}
    <!-- Sidebar content -->
{% endblock %}
```

## Layout Components Reference

### Page Wrapper (`page_wrapper.html`)
Controls the overall page container and spacing.

**Parameters:**
- `wrapper_type`: "standard", "fluid", "contained"  
- `extra_classes`: Additional CSS classes

**Usage Examples:**
```html
<!-- Standard layout with padding -->
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" %}

<!-- Full-width layout -->
{% include 'layouts/page_wrapper.html' with wrapper_type="fluid" %}

<!-- Contained layout with max-width -->
{% include 'layouts/page_wrapper.html' with wrapper_type="contained" %}

<!-- With extra classes -->
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" extra_classes="bg-gray-100" %}
```

### Page Header (`page_header.html`)
Provides consistent page titles, descriptions, breadcrumbs, and actions.

**Parameters:**
- `title`: Page title (required)
- `description`: Optional page description  
- `variant`: "standard", "compact", "with-tabs"
- `breadcrumbs`: List of breadcrumb items
- `show_actions`: Boolean to show action area
- `extra_classes`: Additional CSS classes

**Usage Examples:**
```html
<!-- Basic header -->
{% include 'layouts/page_header.html' with title="Dashboard" %}

<!-- Header with description and actions -->
{% include 'layouts/page_header.html' with title="User Management" description="Manage system users and permissions" show_actions=True %}

{% block page_actions %}
    <button class="btn-primary">Add User</button>
    <button class="btn-secondary">Export</button>
{% endblock %}

<!-- Compact header -->
{% include 'layouts/page_header.html' with title="Settings" variant="compact" %}

<!-- Header with breadcrumbs -->
{% include 'layouts/page_header.html' with title="User Profile" breadcrumbs=breadcrumb_data %}
```

**Breadcrumb Format:**
```python
# In your view
breadcrumbs = [
    {'title': 'Dashboard', 'url': '/dashboard/'},
    {'title': 'Users', 'url': '/users/'},
    {'title': 'John Doe', 'url': None}  # Current page, no URL
]
```

### Content Layout (`content_layout.html`)
Flexible content area with optional sidebars.

**Parameters:**
- `layout_type`: "single", "sidebar-right", "sidebar-left", "two-sidebar"
- `sidebar_width`: "narrow", "standard", "wide"
- `extra_classes`: Additional CSS classes

**Usage Examples:**
```html
<!-- Single column -->
{% include 'layouts/content_layout.html' with layout_type="single" %}

{% block primary_content %}
    <div class="p-6">
        <!-- Your content -->
    </div>
{% endblock %}

<!-- Right sidebar -->
{% include 'layouts/content_layout.html' with layout_type="sidebar-right" sidebar_width="standard" %}

{% block primary_content %}
    <!-- Main content -->
{% endblock %}

{% block right_sidebar %}
    <!-- Sidebar content -->
{% endblock %}

<!-- Two sidebars -->
{% include 'layouts/content_layout.html' with layout_type="two-sidebar" %}

{% block left_sidebar %}
    <!-- Left sidebar -->
{% endblock %}

{% block primary_content %}
    <!-- Main content -->
{% endblock %}

{% block right_sidebar %}
    <!-- Right sidebar -->
{% endblock %}
```

### Stats Grid (`stats_grid.html`)
Responsive grid for dashboard statistics.

**Parameters:**
- `stats`: List of stat objects
- `columns`: "2", "3", "4", "6"
- `variant`: "standard", "compact", "large"
- `extra_classes`: Additional CSS classes

**Usage Example:**
```html
{% include 'layouts/stats_grid.html' with stats=dashboard_stats columns="4" variant="standard" %}
```

**Stats Data Format:**
```python
# In your view
stats_data = [
    {
        'title': 'Active Users',
        'value': '1,234',
        'icon': 'users',  # or custom SVG HTML
        'color': 'blue',
        'link': '/users/',
        'description': 'Currently online'
    },
    {
        'title': 'Pending Tasks',
        'value': '56',
        'icon': 'warning',
        'color': 'amber',
        'link': '/tasks/',
        'description': 'Requires attention'
    }
]
```

### Table Layout (`table_layout.html`)
Desktop-optimized table with filters and actions.

**Parameters:**
- `table_id`: Unique identifier (required)
- `title`: Table title
- `show_filters`: Boolean for filter panel
- `show_actions`: Boolean for action panel  
- `show_search`: Boolean for search input
- `sticky_header`: Boolean for sticky headers
- `extra_classes`: Additional CSS classes

**Usage Example:**
```html
{% include 'layouts/table_layout.html' with table_id="users-table" title="System Users" show_filters=True show_actions=True show_search=True %}

{% block table_filters %}
    <select class="form-input">
        <option>All Departments</option>
        <option>Engineering</option>
        <option>Operations</option>
    </select>
{% endblock %}

{% block table_actions %}
    <button class="btn-primary">Add User</button>
    <button class="btn-secondary">Export</button>
{% endblock %}

{% block table_head %}
    <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Department</th>
        <th>Status</th>
        <th>Actions</th>
    </tr>
{% endblock %}

{% block table_body %}
    {% for user in users %}
    <tr>
        <td>{{ user.name }}</td>
        <td>{{ user.email }}</td>
        <td>{{ user.department }}</td>
        <td>
            <span class="badge badge-success">Active</span>
        </td>
        <td>
            <button class="btn-sm btn-secondary">Edit</button>
        </td>
    </tr>
    {% endfor %}
{% endblock %}

{% block table_footer %}
    <!-- Pagination -->
    <div>Showing 1-10 of 100 results</div>
    <div>
        <button class="btn-secondary btn-sm">Previous</button>
        <button class="btn-secondary btn-sm">Next</button>
    </div>
{% endblock %}
```

## CSS Classes Reference

### Layout Classes
```css
/* Page Wrappers */
.page-wrapper-standard    /* Standard contained layout */
.page-wrapper-fluid       /* Full-width layout */
.page-wrapper-contained   /* Max-width contained layout */

/* Desktop Grid System */
.desktop-grid            /* Base grid container */
.desktop-grid-1          /* 1 column */
.desktop-grid-2          /* 2 columns */
.desktop-grid-3          /* 3 columns */
.desktop-grid-4          /* 4 columns */
.desktop-grid-6          /* 6 columns */
```

### Component Classes
```css
/* Buttons */
.btn                     /* Base button */
.btn-primary            /* Primary button */
.btn-secondary          /* Secondary button */
.btn-success            /* Success button */
.btn-warning            /* Warning button */
.btn-danger             /* Danger button */
.btn-sm                 /* Small button */
.btn-lg                 /* Large button */

/* Cards */
.card                   /* Base card */
.card-elevated          /* Card with shadow */
.card-interactive       /* Clickable card */
.card-header           /* Card header section */
.card-content          /* Card content section */
.card-footer           /* Card footer section */

/* Forms */
.form-input            /* Form input styling */
.form-label            /* Form label styling */
.form-section          /* Form section container */

/* Status Badges */
.badge                 /* Base badge */
.badge-success         /* Success badge */
.badge-warning         /* Warning badge */
.badge-error           /* Error badge */
.badge-info            /* Info badge */
.badge-neutral         /* Neutral badge */

/* Utilities */
.focus-ring            /* Enhanced focus ring */
.hover-lift            /* Hover lift effect */
.hover-shadow          /* Hover shadow effect */
```

## Responsive Behavior

### Breakpoints
- **Mobile**: < 768px (48rem)
- **Tablet**: 768px - 1024px (48rem - 64rem)  
- **Desktop**: 1024px - 1440px (64rem - 90rem)
- **Wide**: 1440px+ (90rem+)

### Grid Responsive Behavior
```css
/* Stats Grid Example */
Mobile:   1 column
Tablet:   2 columns  
Desktop:  4 columns
Wide:     6 columns
```

### Sidebar Behavior
```css
/* Content Layout Sidebars */
Mobile:   Stack vertically, full width
Tablet:   Single sidebar only
Desktop:  Side-by-side layout
Wide:     Larger sidebar widths
```

## Page Type Templates

### 1. Dashboard Page
```html
{% extends 'base.html' %}

{% block content %}
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" %}

{% block page_content %}
    {% include 'layouts/page_header.html' with title="Dashboard" description="Overview of your system" %}
    
    <!-- Stats Section -->
    {% include 'layouts/stats_grid.html' with stats=dashboard_stats columns="4" %}
    
    {% include 'layouts/content_layout.html' with layout_type="sidebar-right" %}
    
    {% block primary_content %}
        <!-- Main dashboard content -->
    {% endblock %}
    
    {% block right_sidebar %}
        <!-- Recent activity, quick actions -->
    {% endblock %}
{% endblock %}
{% endblock %}
```

### 2. List/Table Page
```html
{% extends 'base.html' %}

{% block content %}
{% include 'layouts/page_wrapper.html' with wrapper_type="fluid" %}

{% block page_content %}
    {% include 'layouts/page_header.html' with title="Users" show_actions=True %}
    
    {% block page_actions %}
        <button class="btn-primary">Add User</button>
    {% endblock %}
    
    {% include 'layouts/table_layout.html' with table_id="users-table" show_filters=True show_search=True %}
    <!-- Table content blocks -->
{% endblock %}
{% endblock %}
```

### 3. Form Page
```html
{% extends 'base.html' %}

{% block content %}
{% include 'layouts/page_wrapper.html' with wrapper_type="contained" %}

{% block page_content %}
    {% include 'layouts/page_header.html' with title="Edit Profile" variant="compact" %}
    
    {% include 'layouts/content_layout.html' with layout_type="sidebar-right" %}
    
    {% block primary_content %}
        <div class="p-6">
            <form class="space-y-6">
                <!-- Form sections -->
            </form>
        </div>
    {% endblock %}
    
    {% block right_sidebar %}
        <!-- Help text, preview, etc. -->
    {% endblock %}
{% endblock %}
{% endblock %}
```

### 4. Detail Page
```html
{% extends 'base.html' %}

{% block content %}
{% include 'layouts/page_wrapper.html' with wrapper_type="standard" %}

{% block page_content %}
    {% include 'layouts/page_header.html' with title=object.name breadcrumbs=breadcrumbs show_actions=True %}
    
    {% block page_actions %}
        <button class="btn-primary">Edit</button>
        <button class="btn-danger">Delete</button>
    {% endblock %}
    
    {% include 'layouts/content_layout.html' with layout_type="two-sidebar" %}
    
    {% block left_sidebar %}
        <!-- Navigation, metadata -->
    {% endblock %}
    
    {% block primary_content %}
        <!-- Main content -->
    {% endblock %}
    
    {% block right_sidebar %}
        <!-- Related items, actions -->
    {% endblock %}
{% endblock %}
{% endblock %}
```

## Migration from Existing Pages

### Step 1: Identify Page Type
1. **Dashboard**: Has stats, widgets, overview content
2. **List/Table**: Displays tabular data with filters
3. **Form**: Primary purpose is data input
4. **Detail**: Shows detailed information about a single item

### Step 2: Replace Container Structure
```html
<!-- Old -->
<div class="max-w-7xl mx-auto p-6">
    <!-- content -->
</div>

<!-- New -->
{% include 'layouts/page_wrapper.html' with wrapper_type="contained" %}
{% block page_content %}
    <!-- content -->
{% endblock %}
```

### Step 3: Replace Headers
```html
<!-- Old -->
<div class="mb-6">
    <h1 class="text-3xl font-bold">Page Title</h1>
    <p class="text-gray-600">Description</p>
</div>

<!-- New -->
{% include 'layouts/page_header.html' with title="Page Title" description="Description" %}
```

### Step 4: Replace Layout Structure
```html
<!-- Old grid layout -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2"><!-- Main --></div>
    <div><!-- Sidebar --></div>
</div>

<!-- New layout system -->
{% include 'layouts/content_layout.html' with layout_type="sidebar-right" %}
{% block primary_content %}<!-- Main -->{% endblock %}
{% block right_sidebar %}<!-- Sidebar -->{% endblock %}
```

### Step 5: Replace Component Classes
```html
<!-- Old custom classes -->
<button class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">

<!-- New component classes -->
<button class="btn-primary">
```

## Best Practices

### 1. Semantic HTML
- Use proper heading hierarchy (h1 → h2 → h3)
- Use `<main>`, `<section>`, `<article>` appropriately  
- Add ARIA labels for screen readers

### 2. Accessibility
- Include focus management for interactive elements
- Use proper form labels and descriptions
- Provide alternative text for images
- Ensure sufficient color contrast

### 3. Performance
- Minimize custom CSS, use component classes
- Optimize images and use appropriate formats
- Lazy load content when appropriate

### 4. Responsive Design
- Test on multiple screen sizes
- Ensure touch targets are large enough (44px minimum)
- Use appropriate font sizes for different screens

### 5. Content Organization
- Group related content in sections
- Use consistent spacing and typography
- Prioritize important content for mobile viewports

## Troubleshooting

### Common Issues

**Issue: Layout not responsive**
- Check that you're using the correct wrapper type
- Ensure content layout type is appropriate for content
- Verify CSS classes are applied correctly

**Issue: Sidebar not showing on mobile**  
- This is expected behavior - sidebars stack on mobile
- Use `lg:hidden` and `lg:block` classes if needed

**Issue: Buttons not styled correctly**
- Make sure you're using component classes (`.btn-primary`)
- Add `focus-ring` class for accessibility
- Check for conflicting CSS classes

**Issue: Forms not accessible**
- Use proper form labels with `form-label` class
- Add `focus-ring` to form inputs
- Include error messaging with proper ARIA attributes

### Getting Help
1. Check the component documentation
2. Review existing page examples
3. Test on multiple screen sizes
4. Validate HTML and accessibility
5. Ask the development team for code review

## Examples Repository
See the `frontend/templates/pages/profile_new_layout.html` file for a complete example of the new layout system in action.