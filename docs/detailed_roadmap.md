# TPS V1.4 Complete Transformation Roadmap - Detailed Version

## Executive Summary of Issues Found

### Critical Issues Discovered:
1. **Massive Duplication**: Found duplicate files in `/frontend/static/` and `/staticfiles/` directories
2. **Mixed Authentication**: Using both session auth and JWT tokens inconsistently
3. **No User Roles**: User model lacks role field despite role-based UI requirements
4. **Incomplete WebSocket**: WebSocket handlers exist but aren't properly connected
5. **Hardcoded Teams**: Multiple places with hardcoded team IDs (1,2,3)
6. **Missing Models**: No models for leave requests, shift swaps, or notifications
7. **API Versioning Chaos**: v1 and v2 APIs mixed without clear migration path
8. **No Test Coverage**: Zero test files found in the project
9. **Planning Algorithm Issues**: Complex planning logic spread across multiple files
10. **UI Component Mess**: Components import each other creating circular dependencies

## Phase 0: Emergency Fixes (Week 0 - URGENT)

### Step 0.1: Remove All Duplicate Files
**Current State:**
- `/frontend/static/js/components/` has 15+ components
- `/staticfiles/js/components/` has identical copies
- This causes confusion and maintenance nightmares

**AI Prompt:**
```
I have duplicate JavaScript files in two directories:
1. /frontend/static/js/components/
2. /staticfiles/js/components/

The staticfiles directory seems to be a Django collectstatic output that was accidentally committed. 

Please:
1. Create a script to identify all duplicate files between these directories
2. Remove the /staticfiles/ directory from version control
3. Update .gitignore to exclude staticfiles/
4. Update all import paths to use /frontend/static/
5. Create a file cleanup script: scripts/cleanup_duplicates.py
```

### Step 0.2: Fix Circular Dependencies
**Current Issues Found:**
- notification-handler.js imports from window.TPSApp
- planning-wizard.js references components not yet loaded
- app.js initialization order is wrong

**AI Prompt:**
```
Fix circular dependencies in TPS V1.4 JavaScript components:

Current problematic imports:
- notification-handler.js uses window.TPSApp?.components?.planningWizard
- planning-wizard.js uses window.TPSApp?.utils
- Multiple components assume others are already initialized

Create:
1. frontend/static/js/core/dependency-manager.js - Manages component loading order
2. frontend/static/js/core/event-bus.js - Decoupled event communication
3. Update all components to use event-based communication
4. Create initialization pipeline that ensures proper load order
```

### Step 0.3: Database Model Fixes
**Missing Models Identified:**
- No LeaveRequest model
- No ShiftSwapRequest model  
- No Notification model
- No TeamMembership model
- No UserPreferences model
- No PlanningTemplate model

**AI Prompt:**
```
Create missing Django models for TPS V1.4:

1. apps/leave/models.py:
   - LeaveRequest (user, start_date, end_date, type, status, reason, approved_by)
   - LeaveBalance (user, year, entitled_days, used_days, remaining_days)
   - LeaveType (name, code, requires_approval, max_days)

2. apps/shifts/models.py:
   - ShiftSwapRequest (requester, target_user, shift, new_shift, status, reason)
   - ShiftTemplate (name, start_time, end_time, break_duration, skills_required)
   - RecurringShift (template, days_of_week, team)

3. apps/notifications/models.py:
   - Notification (user, type, title, message, data, read, created_at)
   - NotificationPreference (user, notification_type, email, push, in_app)

4. apps/teams/models.py additions:
   - TeamMembership (user, team, role, joined_at, left_at, is_active)
   - TeamSettings (team, planning_horizon, min_staff, max_overtime)

Include migrations and admin registration for all models.
```

## Phase 1: Backend Architecture Overhaul (Week 1-2)

### Step 1.1: Complete API Restructure
**Current Problems:**
- api/v1/analytics.py and analytics_overview.py have 80% overlap
- api/v1/teams_enhanced.py duplicates teams_overview.py functionality  
- No consistent error handling across endpoints
- Missing pagination on list endpoints
- No API documentation

**AI Prompt:**
```
Completely restructure TPS V1.4 API architecture:

Current duplicate/problematic files:
- api/v1/analytics.py (276 lines)
- api/v1/analytics_overview.py (189 lines) 
- api/v1/teams_enhanced.py (245 lines)
- api/v1/teams_overview.py (156 lines)

Create clean API v2 structure:
1. api/v2/__init__.py
2. api/v2/views/
   - teams.py (merge all team endpoints)
   - planning.py (extract from planning_detail.py, planning_manual.py)
   - analytics.py (merge all analytics)
   - users.py (user management endpoints)
   - shifts.py (shift management)
   - leave.py (leave requests)
   - notifications.py

3. api/v2/serializers/
   - Complete DRF serializers for all models
   
4. api/v2/permissions.py
   - IsPlannerOrAbove
   - IsManagerOrAbove  
   - IsTeamMember
   - IsOwnerOrPlanner

5. api/v2/mixins.py
   - PaginationMixin
   - ErrorHandlingMixin
   - CacheResponseMixin

6. api/v2/docs.py
   - OpenAPI schema generation
```

### Step 1.2: Implement Proper User Role System
**Current State:**
- User model has no role field
- Frontend expects role-based views but backend doesn't support it
- No role checking in views

**AI Prompt:**
```
Implement complete role-based access control for TPS V1.4:

1. Update User model:
   - Add role field with choices: USER, PLANNER, MANAGER, ADMIN
   - Add migration to set existing users to USER role
   - Add is_planner, is_manager properties

2. Create apps/users/permissions.py:
   - Role-based permission classes
   - Team-based permission classes
   - Object-level permissions

3. Create apps/users/middleware.py:
   - RoleMiddleware to inject user role into requests
   - TeamContextMiddleware for team-scoped requests

4. Update all views to use permissions:
   - Planning views require PLANNER role
   - Analytics views require MANAGER role
   - Shift views check team membership

5. Create role management commands:
   - python manage.py assign_role <username> <role>
   - python manage.py list_roles
```

### Step 1.3: Fix Authentication Chaos
**Problems Found:**
- Some views use @login_required
- Others use @api_view without authentication
- JWT tokens generated but not consistently used
- Session auth mixed with token auth

**AI Prompt:**
```
Standardize authentication in TPS V1.4:

Current issues:
- Mixed session and JWT authentication
- Inconsistent decorator usage
- No token refresh mechanism
- Missing authentication on critical endpoints

Implement:
1. core/authentication.py:
   - TPSTokenAuthentication class
   - Support both session and token auth
   - Automatic token refresh

2. Update settings.py:
   - Configure DRF authentication classes
   - Set token expiry times
   - Configure CORS properly

3. Create authentication views:
   - api/v2/auth/login.py (return token + user data)
   - api/v2/auth/refresh.py (refresh token)
   - api/v2/auth/logout.py (invalidate token)

4. Update all API views:
   - Add authentication_classes
   - Add permission_classes
   - Remove @login_required, use DRF authentication

5. Frontend token management:
   - services/auth-service.js
   - Automatic token refresh
   - Redirect on 401
```

## Phase 2: Frontend Architecture Rebuild (Week 3-4)

### Step 2.1: Component Library with Proper Structure
**Current Component Issues:**
- No base component class
- Inconsistent initialization
- Direct DOM manipulation everywhere
- No component lifecycle
- Memory leaks from event listeners

**AI Prompt:**
```
Create proper component architecture for TPS V1.4:

Problems in current components:
- Inconsistent constructor patterns
- Direct window.TPSApp access
- No cleanup on component destroy
- Inline styles instead of CSS classes
- No state management

Create new architecture:
1. frontend/static/js/core/Component.js:
   ```javascript
   export class Component extends HTMLElement {
     constructor() { super(); }
     connectedCallback() { }
     disconnectedCallback() { }
     attributeChangedCallback(name, oldValue, newValue) { }
     setState(newState) { }
     render() { }
   }
   ```

2. Refactor all components to extend Component:
   - tps-calendar
   - tps-shift-card  
   - tps-team-selector
   - tps-notification
   - tps-planning-wizard
   - tps-analytics-chart

3. Create component registry:
   - frontend/static/js/core/registry.js
   - Auto-register all components
   - Handle lazy loading

4. State management:
   - frontend/static/js/core/Store.js
   - Observable state pattern
   - Components subscribe to state changes

5. CSS architecture:
   - frontend/static/css/components/base.css
   - One CSS file per component
   - CSS custom properties for theming
```

### Step 2.2: Role-Based UI Implementation
**Current Problems:**
- No role detection in frontend
- All users see same interface
- Menu items not filtered by role
- No role-based routing

**AI Prompt:**
```
Implement role-based UI in TPS V1.4 frontend:

Current issues:
- templates/includes/menu.html shows all items to all users
- No role checking in JavaScript
- Dashboard loads same view for everyone

Create role-based system:
1. frontend/static/js/services/user-service.js:
   - getCurrentUser() with role
   - hasRole(role) helper
   - canAccess(feature) helper

2. frontend/static/js/core/Router.js:
   - Role-based route guards
   - Redirect unauthorized access
   - Dynamic route registration

3. Update templates:
   - templates/includes/menu_planner.html
   - templates/includes/menu_manager.html  
   - templates/includes/menu_user.html
   - templates/base.html conditionally includes based on user.role

4. Create role-specific dashboards:
   - static/js/pages/planner-dashboard.js
   - static/js/pages/manager-dashboard.js
   - static/js/pages/user-dashboard.js

5. Component visibility:
   - Add data-require-role attribute
   - RoleVisibility directive
   - Hide/show based on user role
```

### Step 2.3: Responsive Mobile Design
**Current Issues:**
- Tables break on mobile
- Calendar unusable on small screens
- No touch gesture support
- Fixed widths everywhere
- No mobile navigation

**AI Prompt:**
```
Make TPS V1.4 fully mobile responsive:

Current problems:
- Fixed width tables (width: 800px)
- Desktop-only hover states
- No mobile navigation menu
- Calendar doesn't fit mobile screens
- Modals too large for mobile

Implement:
1. frontend/static/css/mobile.css:
   - Mobile-first breakpoints
   - Touch-friendly tap targets (min 44px)
   - Swipeable calendar views
   - Collapsible table columns
   - Bottom navigation for mobile

2. frontend/static/js/utils/responsive-tables.js:
   - Convert tables to cards on mobile
   - Priority column hiding
   - Horizontal scroll with indicators

3. frontend/static/js/utils/touch-gestures.js:
   - Swipe to change calendar week/month
   - Pull to refresh
   - Long press for context menu
   - Pinch to zoom calendar

4. Update all components:
   - Remove fixed widths
   - Use CSS Grid/Flexbox
   - Add mobile-specific layouts
   - Touch-friendly interactions

5. Progressive Web App:
   - manifest.json
   - Service worker for offline
   - Install prompt
   - Push notifications
```

## Phase 3: Real-Time Features (Week 5)

### Step 3.1: Complete WebSocket Implementation
**Current State:**
- WebSocket consumers exist but aren't connected
- No routing configuration
- Frontend doesn't establish WebSocket connection
- No reconnection logic

**AI Prompt:**
```
Complete WebSocket implementation for TPS V1.4:

Current incomplete files:
- apps/websockets/consumers.py (partial)
- No websocket routing
- No frontend WebSocket service

Implement complete real-time system:
1. apps/websockets/consumers.py:
   - PlanningConsumer (planning progress)
   - TeamConsumer (team updates)
   - NotificationConsumer (user notifications)
   - PresenceConsumer (online status)

2. apps/websockets/routing.py:
   - URL patterns for consumers
   - Authentication middleware
   - Team-based channel groups

3. tps_system/asgi.py:
   - Configure ASGI application
   - WebSocket protocol routing

4. frontend/static/js/services/websocket-service.js:
   - Connection management
   - Auto-reconnect with backoff
   - Message queuing while disconnected
   - Event emitter pattern

5. Real-time features:
   - Live planning updates
   - Instant notifications
   - User presence indicators
   - Collaborative editing
```

### Step 3.2: Notification System
**Current Issues:**
- Notification handler exists but no backend
- No notification preferences
- No notification history
- No push notifications

**AI Prompt:**
```
Build complete notification system for TPS V1.4:

Implement:
1. Backend notification system:
   - apps/notifications/services.py
   - NotificationService class
   - Send via WebSocket, email, push
   - Notification templates
   - Preference checking

2. Notification types:
   - ShiftAssignedNotification
   - ShiftChangeNotification
   - LeaveRequestNotification
   - SwapRequestNotification
   - PlanningCompleteNotification
   - SystemAnnouncementNotification

3. Frontend notification center:
   - components/notification-center.js
   - Notification list with filters
   - Mark as read/unread
   - Notification preferences UI
   - Desktop notification permission

4. Push notifications:
   - Web Push implementation
   - Service worker for background
   - Subscription management
   - Fallback to in-app only

5. Email notifications:
   - HTML email templates
   - Batching for digest emails
   - Unsubscribe links
   - Template preview system
```

## Phase 4: Planning System Overhaul (Week 6)

### Step 4.1: Consolidate Planning Logic
**Current Mess:**
- Planning logic split across multiple files
- Orchestrator pattern but incomplete implementation
- Manual planning disconnected from auto planning
- No planning templates

**AI Prompt:**
```
Refactor entire planning system in TPS V1.4:

Current problematic structure:
- apps/planning/orchestrator.py
- apps/planning/manual_planning_processor.py  
- api/v1/planning_manual.py
- api/v1/planning_detail.py
- staticfiles/js/planning-drag-drop.js

Create unified planning system:
1. apps/planning/services/planning_service.py:
   - Single entry point for all planning
   - Support manual and auto modes
   - Planning templates
   - Constraint validation
   - Conflict resolution

2. apps/planning/algorithms/:
   - base_algorithm.py (abstract base)
   - greedy_algorithm.py
   - balanced_algorithm.py
   - ai_algorithm.py (future ML)

3. apps/planning/validators/:
   - shift_validator.py
   - availability_validator.py
   - skill_validator.py
   - overtime_validator.py

4. apps/planning/models.py additions:
   - PlanningTemplate model
   - PlanningRun model
   - PlanningConstraint model

5. Frontend planning UI:
   - Unified planning wizard
   - Drag-drop interface
   - Real-time validation
   - Progress tracking
   - Undo/redo support
```

### Step 4.2: Planning Analytics
**Missing Feature:**
- No planning quality metrics
- No historical comparison
- No optimization suggestions

**AI Prompt:**
```
Add planning analytics to TPS V1.4:

Create:
1. apps/planning/analytics.py:
   - Planning quality score
   - Coverage analysis
   - Cost analysis
   - Fairness metrics
   - Efficiency ratings

2. apps/planning/reports.py:
   - Planning comparison reports
   - What-if analysis
   - Optimization suggestions
   - Constraint violation reports

3. Frontend planning analytics:
   - components/planning-analytics.js
   - Quality score dashboard
   - Comparison charts
   - Suggestion panel
   - Export to PDF/Excel
```

## Phase 5: Data Management (Week 7)

### Step 5.1: Import/Export System
**Current State:**
- No data import capabilities
- Limited export options
- No bulk operations

**AI Prompt:**
```
Build comprehensive import/export system for TPS V1.4:

Implement:
1. apps/data/importers/:
   - excel_importer.py (users, shifts, teams)
   - csv_importer.py
   - legacy_system_importer.py
   - Validation and error reporting

2. apps/data/exporters/:
   - excel_exporter.py
   - pdf_exporter.py
   - ical_exporter.py (calendar)
   - api_exporter.py (for integrations)

3. apps/data/templates/:
   - Excel templates for import
   - PDF report templates
   - Email templates

4. Frontend import/export UI:
   - components/data-import-wizard.js
   - Drag-drop file upload
   - Preview before import
   - Error handling UI
   - Progress tracking

5. Scheduled exports:
   - Weekly team reports
   - Monthly analytics
   - Planning summaries
```

### Step 5.2: Audit Trail
**Missing Feature:**
- No change tracking
- No audit logs
- Can't see who changed what

**AI Prompt:**
```
Implement audit trail system for TPS V1.4:

Create:
1. apps/audit/models.py:
   - AuditLog model
   - Track all changes
   - Store old/new values
   - User and timestamp

2. apps/audit/middleware.py:
   - AutoAuditMiddleware
   - Capture all model changes
   - Track API access

3. apps/audit/views.py:
   - Audit log viewer
   - Filter by user/date/model
   - Change comparison view

4. Frontend audit UI:
   - components/audit-trail.js
   - Timeline view
   - Diff viewer
   - Filter panel
```

## Phase 6: Performance & Testing (Week 8)

### Step 6.1: Performance Optimization
**Current Issues:**
- No query optimization
- Missing database indexes
- No caching strategy
- Large JavaScript bundles

**AI Prompt:**
```
Optimize TPS V1.4 performance:

Database optimization:
1. Create apps/core/management/commands/optimize_db.py:
   - Analyze slow queries
   - Suggest indexes
   - Add missing foreign key indexes
   - Optimize N+1 queries

2. Query optimization:
   - Use select_related/prefetch_related
   - Add database views for complex queries
   - Implement query result caching

3. Frontend optimization:
   - Code splitting by route
   - Lazy load components
   - Image optimization
   - Critical CSS inline
   - Tree shaking unused code

4. Caching strategy:
   - Redis for API responses
   - Browser caching headers
   - Service worker caching
   - CDN for static assets

5. Monitoring:
   - Django Debug Toolbar setup
   - Frontend performance metrics
   - APM integration
   - Slow query alerts
```

### Step 6.2: Comprehensive Testing
**Current State:**
- Zero test files found
- No test configuration
- No CI/CD pipeline

**AI Prompt:**
```
Create complete test suite for TPS V1.4:

1. Backend tests structure:
   tests/
   ├── unit/
   │   ├── test_models.py
   │   ├── test_services.py
   │   ├── test_utils.py
   │   └── test_algorithms.py
   ├── integration/
   │   ├── test_api_auth.py
   │   ├── test_api_teams.py
   │   ├── test_api_planning.py
   │   └── test_websockets.py
   ├── e2e/
   │   ├── test_planning_flow.py
   │   ├── test_leave_request_flow.py
   │   └── test_shift_swap_flow.py
   └── fixtures/

2. Frontend tests:
   frontend/tests/
   ├── components/
   │   ├── test_calendar.js
   │   ├── test_planning_wizard.js
   │   └── test_notifications.js
   ├── services/
   │   ├── test_api_service.js
   │   └── test_websocket_service.js
   └── e2e/
       └── cypress/

3. Test configuration:
   - pytest.ini
   - .coveragerc
   - jest.config.js
   - cypress.json

4. CI/CD pipeline:
   - .github/workflows/tests.yml
   - Run on all PRs
   - Coverage reports
   - Automated deployment

5. Test data factories:
   - tests/factories.py
   - Realistic test data
   - Consistent scenarios
```

## Phase 7: Documentation (Ongoing)

### Step 7.1: User Documentation
**AI Prompt:**
```
Create user documentation for TPS V1.4:

1. docs/user-guide/:
   - getting-started.md
   - planner-guide.md
   - manager-guide.md
   - user-guide.md
   - faq.md

2. In-app help:
   - Contextual help tooltips
   - Interactive tutorials
   - Video walkthroughs

3. API documentation:
   - OpenAPI/Swagger spec
   - Postman collection
   - Example requests
```

### Step 7.2: Developer Documentation
**AI Prompt:**
```
Create developer documentation:

1. docs/developer/:
   - architecture.md
   - setup-guide.md
   - api-reference.md
   - component-guide.md
   - deployment.md

2. Code documentation:
   - Docstrings for all functions
   - Type hints everywhere
   - JSDoc for JavaScript
   - Architecture diagrams

3. Contributing guide:
   - CONTRIBUTING.md
   - Code style guide
   - PR template
   - Issue templates
```

## Immediate Action Items

### Week 0 - Emergency Fixes:
1. Delete `/staticfiles/` directory
2. Fix circular dependencies
3. Add missing models
4. Fix authentication

### Week 1-2 - Backend:
1. Consolidate APIs
2. Implement roles
3. Add caching
4. Create missing endpoints

### Week 3-4 - Frontend:
1. Component library
2. Role-based UI
3. Mobile responsive
4. Remove duplicates

### Week 5-6 - Features:
1. WebSockets
2. Notifications
3. Planning overhaul
4. Analytics

### Week 7-8 - Polish:
1. Import/Export
2. Performance
3. Testing
4. Documentation

## Success Criteria
- Zero duplicate code
- 100% mobile responsive
- < 200ms API response time
- > 80% test coverage
- Real-time updates working
- Role-based UI complete
- All validations in place
- Comprehensive audit trail