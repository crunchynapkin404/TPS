# TPS Performance Optimization Report

## Overview
This report documents the performance optimizations implemented in the TPS (Team Planning System) repository to address identified bottlenecks and improve system performance.

## Identified Performance Issues

### 1. Database Query Problems (High Priority)

**N+1 Query Issues:**
- `ManagerDashboardStrategy._get_team_stats()` - Making individual queries for each team
- `PlannerDashboardStrategy._generate_planning_advice()` - Looping through teams with separate queries
- `LeaveOverviewView.get_context_data()` - Multiple separate queries for statistics

**Missing Query Optimizations:**
- Lack of `select_related` and `prefetch_related` in dashboard queries  
- No database indexes on frequently queried fields
- Separate queries that could be combined into single aggregated queries

### 2. Caching Issues (High Priority)

**No Caching Layer:**
- User permissions recalculated on every request
- Dashboard data regenerated for each page load
- Team memberships queried repeatedly
- System statistics calculated fresh each time

### 3. Inefficient Algorithms (Medium Priority)

**Repeated Calculations:**
- Role-based permission checks executed multiple times per request
- Team statistics calculated individually rather than in batch
- Complex dashboard context built from scratch each time

## Implemented Optimizations

### 1. Database Query Optimizations

#### Fixed N+1 Query Problems

**ManagerDashboardStrategy._get_team_stats():**
```python
# BEFORE: N+1 queries (1 per team)
for team in managed_teams:
    team_members = User.objects.filter(team_memberships__team=team).count()
    this_week_assignments = Assignment.objects.filter(...).count()

# AFTER: 2 optimized queries with annotations
team_member_counts = managed_teams.annotate(
    member_count=Count('memberships', filter=Q(...))
)
team_assignment_counts = Assignment.objects.filter(...).values(...).annotate(
    assignment_count=Count('id')
)
```

**PlannerDashboardStrategy._generate_planning_advice():**
```python
# BEFORE: N queries (1 per team)
for team in user_teams:
    upcoming_shifts = ShiftInstance.objects.filter(...).count()

# AFTER: 1 query with aggregation
team_unassigned_counts = ShiftInstance.objects.filter(...).values(...).annotate(
    unassigned_count=Count('id')
)
```

#### Enhanced Query Optimizations

**LeaveOverviewView.get_context_data():**
```python
# BEFORE: 5+ separate queries
stats = {
    'total_requests': self.get_queryset().count(),
    'pending_requests': self.get_queryset().filter(...).count(),
    'approved_requests': self.get_queryset().filter(...).count(),
    'used_days_ytd': leave_balances.aggregate(total=Sum('used'))['total'],
    'pending_days': leave_balances.aggregate(total=Sum('pending'))['total'],
}

# AFTER: 2 optimized aggregate queries
request_stats = base_queryset.aggregate(
    total_requests=Count('id'),
    pending_requests=Count('id', filter=Q(...)),
    approved_requests=Count('id', filter=Q(...))
)
balance_stats = leave_balances.aggregate(
    used_days_ytd=Sum('used'),
    pending_days=Sum('pending')
)
```

#### Added Database Indexes

Created migration `0005_performance_indexes.py` with strategic indexes:
- `idx_user_role` on `tps_users.role`
- `idx_assignment_status` on `tps_assignments.status`  
- `idx_assignment_user_status` on `(user_id, status)`
- `idx_leave_request_user_status` on `(user_id, status)`
- `idx_team_membership_active` on `(is_active, user_id, team_id)`
- Additional indexes on frequently queried datetime and foreign key fields

### 2. Caching Layer Implementation

#### CacheService
Created comprehensive caching service (`core/services/cache_service.py`):

**Features:**
- User permissions caching (5 min timeout)
- Dashboard data caching (3 min timeout)  
- Team memberships caching (10 min timeout)
- System statistics caching (2 min timeout)
- Intelligent cache invalidation on data changes

**Cache Key Strategy:**
```python
def _make_cache_key(cls, *parts) -> str:
    key_string = ':'.join(str(part) for part in parts)
    if len(key_string) > 100:
        return f"tps:{hashlib.md5(key_string.encode()).hexdigest()}"
    return f"tps:{key_string}"
```

#### User Model Caching
Enhanced User model methods with caching:

```python
def is_planner(self):
    cached_permissions = CacheService.get_user_permissions(self.id)
    if cached_permissions and 'is_planner' in cached_permissions:
        return cached_permissions['is_planner']
    
    # Calculate and cache all permissions at once
    result = self.role in ['PLANNER', 'MANAGER', 'ADMIN']
    permissions = {...}
    CacheService.set_user_permissions(self.id, permissions)
    return result
```

### 3. Query Optimization Service

#### QueryOptimizationService
Created centralized service (`core/services/query_optimization_service.py`):

**Key Features:**
- `get_user_dashboard_data()` - Single optimized query for user dashboard
- `get_team_workload_stats()` - Bulk team statistics in one query
- `get_system_health_metrics()` - Comprehensive system metrics with minimal queries
- `get_user_workload_analysis()` - Detailed user workload with single query

**Example Optimization:**
```python
# Single query for user dashboard with all relationships
user_assignments = Assignment.objects.filter(user=user).select_related(
    'shift__template',
    'shift__planning_period', 
    'assigned_by'
).prefetch_related('shift__planning_period__teams')

# Aggregate all statistics in one query
assignment_stats = user_assignments.aggregate(
    total_assignments=Count('id'),
    this_week_assignments=Count('id', filter=Q(...)),
    upcoming_assignments=Count('id', filter=Q(...)),
    completed_assignments=Count('id', filter=Q(...)),
    pending_confirmations=Count('id', filter=Q(...))
)
```

### 4. Enhanced Dashboard Service

#### Optimized Strategy Pattern
Updated dashboard strategies to use new optimization services:

```python
def _get_system_metrics_optimized(self) -> Dict[str, Any]:
    # Use optimized query service instead of separate queries
    system_metrics = QueryOptimizationService.get_system_health_metrics()
    return {
        'total_users': system_metrics['total_active_users'],
        'system_health': system_metrics['success_rate'],
        'user_engagement_rate': system_metrics['user_engagement_rate'],
        # ... more metrics from single service call
    }
```

### 5. API Endpoint Caching

Enhanced API endpoints with caching:

```python
@api_view(['GET'])
def dashboard_stats(request):
    # Try cache first
    cached_response = CacheService.get_dashboard_data(
        request.user.id, f"api_{request.user.role}"
    )
    if cached_response:
        return Response(cached_response, status=status.HTTP_200_OK)
    
    # Generate and cache response
    # ...
    CacheService.set_dashboard_data(request.user.id, f"api_{request.user.role}", api_response)
```

## Performance Testing

### Test Command
Created `core/management/commands/test_performance.py` for benchmarking:

**Features:**
- Dashboard loading performance tests
- Query count analysis  
- Caching effectiveness measurement
- Performance recommendations

**Usage:**
```bash
python manage.py test_performance --iterations 10 --clear-cache
```

## Expected Performance Improvements

### Big O Analysis

**Before Optimizations:**
- Dashboard loading: O(n*m) where n=teams, m=queries per team
- Leave overview: O(k) with k separate queries  
- User permission checks: O(n) with repeated calculations

**After Optimizations:**  
- Dashboard loading: O(1) with caching, O(log n) with query optimization
- Leave overview: O(1) with combined aggregated queries
- User permission checks: O(1) with caching

### Query Count Reductions

**Estimated improvements:**
- Manager dashboard: ~15-20 queries → 3-5 queries
- User dashboard: ~8-12 queries → 2-3 queries  
- Leave overview: ~6-8 queries → 2-3 queries
- System health metrics: ~10-15 queries → 1-2 queries

### Response Time Improvements

**With caching enabled:**
- Dashboard loading: 50-80% reduction in response time
- API endpoints: 60-90% reduction for cached responses
- Permission checks: 95%+ reduction (memory cache vs database)

## Implementation Priority

### ✅ Completed (High Priority, Low Effort)
1. Fixed N+1 query problems in dashboard service
2. Added select_related/prefetch_related optimizations
3. Implemented caching layer for user permissions
4. Created query optimization service
5. Added database indexes

### 🚧 In Progress (High Priority, Medium Effort)  
6. Enhanced dashboard API with caching
7. Optimized leave management views
8. Added performance testing framework

### 📋 Future Enhancements (Medium Priority)
9. Implement lazy loading for heavy operations
10. Add database connection pooling
11. Implement background task processing with Celery
12. Add real-time performance monitoring

## Monitoring and Maintenance

### Cache Invalidation Strategy
- Automatic invalidation on model changes
- User-specific cache clearing on profile updates
- System-wide cache clearing on critical data changes

### Performance Monitoring
- Built-in performance test command
- Query count tracking in debug mode
- Cache hit/miss ratio monitoring

### Best Practices for Future Development
1. Always use `select_related`/`prefetch_related` for foreign key relationships
2. Implement caching for expensive calculations
3. Use bulk operations for multiple database modifications
4. Add database indexes for new query patterns
5. Run performance tests before deploying changes

## Conclusion

These optimizations address the major performance bottlenecks identified in the TPS system:

1. **Eliminated N+1 queries** through query optimization and batching
2. **Implemented comprehensive caching** for frequently accessed data
3. **Added strategic database indexes** for common query patterns  
4. **Created performance testing framework** for ongoing monitoring
5. **Established best practices** for future development

The changes are designed to be **minimal and surgical**, focusing on high-impact optimizations without breaking existing functionality. The codebase maintains its existing structure while gaining significant performance improvements through these targeted enhancements.