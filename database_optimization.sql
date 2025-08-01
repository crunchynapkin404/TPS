-- TPS Database Optimization Script
-- Database performance and integrity enhancements
-- Compatible with both SQLite (development) and PostgreSQL (production)

-- =================================
-- PERFORMANCE INDEXES
-- =================================

-- User-related indexes for frequent lookups
CREATE INDEX IF NOT EXISTS idx_users_employee_id ON tps_users(employee_id);
CREATE INDEX IF NOT EXISTS idx_users_role_active ON tps_users(role, is_active_employee);
CREATE INDEX IF NOT EXISTS idx_users_ytd_tracking ON tps_users(ytd_waakdienst_weeks, ytd_incident_weeks);

-- Team membership optimization
CREATE INDEX IF NOT EXISTS idx_team_memberships_user_active ON tps_team_memberships(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_team_memberships_team_active ON tps_team_memberships(team_id, is_active);
CREATE INDEX IF NOT EXISTS idx_team_memberships_primary ON tps_team_memberships(user_id, is_primary_team);

-- Skill-related indexes
CREATE INDEX IF NOT EXISTS idx_user_skills_user_proficiency ON tps_user_skills(user_id, proficiency_level);
CREATE INDEX IF NOT EXISTS idx_user_skills_certification ON tps_user_skills(is_certified, certification_expiry);
CREATE INDEX IF NOT EXISTS idx_skills_category_active ON tps_skills(category_id, is_active);

-- Shift and assignment optimization
CREATE INDEX IF NOT EXISTS idx_shift_instances_date_status ON tps_shift_instances(date, status);
CREATE INDEX IF NOT EXISTS idx_shift_instances_template_date ON tps_shift_instances(template_id, date);
CREATE INDEX IF NOT EXISTS idx_shift_instances_planning_period ON tps_shift_instances(planning_period_id, date);

-- Assignment tracking
CREATE INDEX IF NOT EXISTS idx_assignments_user_status ON tps_assignments(user_id, status);
CREATE INDEX IF NOT EXISTS idx_assignments_shift_type ON tps_assignments(shift_id, assignment_type);
CREATE INDEX IF NOT EXISTS idx_assignments_date_range ON tps_assignments(assigned_at, status);

-- Swap request optimization
CREATE INDEX IF NOT EXISTS idx_swap_requests_user_status ON tps_swap_requests(requesting_user_id, status);
CREATE INDEX IF NOT EXISTS idx_swap_requests_target_status ON tps_swap_requests(target_user_id, status);
CREATE INDEX IF NOT EXISTS idx_swap_requests_expires ON tps_swap_requests(expires_at, status);

-- Notification system
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON tps_notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON tps_notifications(created_at, notification_type_id);

-- Leave management
CREATE INDEX IF NOT EXISTS idx_leave_requests_user_status ON tps_leave_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_leave_requests_date_range ON tps_leave_requests(start_date, end_date);

-- =================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- =================================

-- User dashboard queries
CREATE INDEX IF NOT EXISTS idx_assignments_user_date_status ON tps_assignments(user_id, assigned_at, status);

-- Shift planning queries
CREATE INDEX IF NOT EXISTS idx_shift_instances_date_template_status ON tps_shift_instances(date, template_id, status);

-- Team workload analysis
CREATE INDEX IF NOT EXISTS idx_assignments_team_period ON tps_assignments(user_id, assigned_at) 
WHERE status IN ('confirmed', 'completed');

-- Skill matching for assignments
CREATE INDEX IF NOT EXISTS idx_user_skills_skill_proficiency ON tps_user_skills(skill_id, proficiency_level, user_id);

-- =================================
-- BUSINESS RULE CONSTRAINTS
-- =================================

-- User constraints
ALTER TABLE tps_users ADD CONSTRAINT check_ytd_waakdienst_limit 
CHECK (ytd_waakdienst_weeks <= 52);

ALTER TABLE tps_users ADD CONSTRAINT check_ytd_incident_limit 
CHECK (ytd_incident_weeks <= 52);

ALTER TABLE tps_users ADD CONSTRAINT check_max_consecutive_days 
CHECK (max_consecutive_days > 0 AND max_consecutive_days <= 14);

-- Team membership constraints
ALTER TABLE tps_team_memberships ADD CONSTRAINT check_availability_percentage 
CHECK (availability_percentage > 0 AND availability_percentage <= 100);

-- Shift instance constraints
ALTER TABLE tps_shift_instances ADD CONSTRAINT check_shift_duration 
CHECK (start_datetime < end_datetime);

-- Assignment constraints
ALTER TABLE tps_assignments ADD CONSTRAINT check_assignment_timing 
CHECK (
    (confirmation_deadline IS NULL OR confirmation_deadline > assigned_at) AND
    (confirmed_at IS NULL OR confirmed_at >= assigned_at) AND
    (completed_at IS NULL OR completed_at >= assigned_at)
);

-- Swap request constraints
ALTER TABLE tps_swap_requests ADD CONSTRAINT check_swap_expiry 
CHECK (expires_at > requested_at);

-- =================================
-- DATA INTEGRITY TRIGGERS (PostgreSQL only)
-- =================================

-- Note: These will only work on PostgreSQL, not SQLite
-- Function to update YTD statistics when assignments are completed
CREATE OR REPLACE FUNCTION update_user_ytd_stats() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        -- Update YTD hours
        UPDATE tps_users 
        SET ytd_hours_logged = ytd_hours_logged + 
            EXTRACT(EPOCH FROM (NEW.actual_end_time - NEW.actual_start_time)) / 3600
        WHERE id = NEW.user_id AND NEW.actual_start_time IS NOT NULL AND NEW.actual_end_time IS NOT NULL;
        
        -- Update YTD week counts based on shift category
        UPDATE tps_users 
        SET ytd_waakdienst_weeks = ytd_waakdienst_weeks + 1
        WHERE id = NEW.user_id 
        AND EXISTS (
            SELECT 1 FROM tps_shift_instances si
            JOIN tps_shift_templates st ON si.template_id = st.id
            JOIN tps_shift_categories sc ON st.category_id = sc.id
            WHERE si.id = NEW.shift_id AND sc.name = 'WAAKDIENST'
        );
        
        UPDATE tps_users 
        SET ytd_incident_weeks = ytd_incident_weeks + 1
        WHERE id = NEW.user_id 
        AND EXISTS (
            SELECT 1 FROM tps_shift_instances si
            JOIN tps_shift_templates st ON si.template_id = st.id
            JOIN tps_shift_categories sc ON st.category_id = sc.id
            WHERE si.id = NEW.shift_id AND sc.name = 'INCIDENT'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for YTD updates
DROP TRIGGER IF EXISTS trigger_update_ytd_stats ON tps_assignments;
CREATE TRIGGER trigger_update_ytd_stats
    AFTER UPDATE ON tps_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_user_ytd_stats();

-- Function to prevent double-booking
CREATE OR REPLACE FUNCTION prevent_double_booking() RETURNS TRIGGER AS $$
BEGIN
    -- Check for overlapping confirmed assignments
    IF EXISTS (
        SELECT 1 FROM tps_assignments a
        JOIN tps_shift_instances si ON a.shift_id = si.id
        WHERE a.user_id = NEW.user_id 
        AND a.status IN ('confirmed', 'completed')
        AND a.assignment_id != NEW.assignment_id
        AND (
            (si.start_datetime, si.end_datetime) OVERLAPS 
            (
                (SELECT start_datetime FROM tps_shift_instances WHERE id = NEW.shift_id),
                (SELECT end_datetime FROM tps_shift_instances WHERE id = NEW.shift_id)
            )
        )
    ) THEN
        RAISE EXCEPTION 'User already has a conflicting assignment during this time period';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent double-booking
DROP TRIGGER IF EXISTS trigger_prevent_double_booking ON tps_assignments;
CREATE TRIGGER trigger_prevent_double_booking
    BEFORE INSERT OR UPDATE ON tps_assignments
    FOR EACH ROW
    WHEN (NEW.status IN ('confirmed', 'completed'))
    EXECUTE FUNCTION prevent_double_booking();

-- =================================
-- QUERY OPTIMIZATION VIEWS
-- =================================

-- View for user workload analysis
CREATE OR REPLACE VIEW user_workload_summary AS
SELECT 
    u.id,
    u.username,
    u.first_name,
    u.last_name,
    u.ytd_waakdienst_weeks,
    u.ytd_incident_weeks,
    u.ytd_hours_logged,
    COUNT(CASE WHEN a.status = 'confirmed' THEN 1 END) as upcoming_assignments,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_assignments,
    AVG(CASE WHEN a.status = 'completed' AND a.actual_start_time IS NOT NULL AND a.actual_end_time IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (a.actual_end_time - a.actual_start_time)) / 3600 END) as avg_hours_per_shift
FROM tps_users u
LEFT JOIN tps_assignments a ON u.id = a.user_id
WHERE u.is_active_employee = true
GROUP BY u.id, u.username, u.first_name, u.last_name, u.ytd_waakdienst_weeks, u.ytd_incident_weeks, u.ytd_hours_logged;

-- View for shift coverage analysis
CREATE OR REPLACE VIEW shift_coverage_analysis AS
SELECT 
    si.date,
    st.name as shift_template_name,
    sc.display_name as category,
    st.engineers_required,
    COUNT(a.id) as assigned_engineers,
    COUNT(CASE WHEN a.status = 'confirmed' THEN 1 END) as confirmed_engineers,
    (st.engineers_required - COUNT(CASE WHEN a.status = 'confirmed' THEN 1 END)) as coverage_gap
FROM tps_shift_instances si
JOIN tps_shift_templates st ON si.template_id = st.id
JOIN tps_shift_categories sc ON st.category_id = sc.id
LEFT JOIN tps_assignments a ON si.id = a.shift_id AND a.assignment_type = 'primary'
WHERE si.date >= CURRENT_DATE
GROUP BY si.id, si.date, st.name, sc.display_name, st.engineers_required
ORDER BY si.date, coverage_gap DESC;

-- View for team performance metrics
CREATE OR REPLACE VIEW team_performance_metrics AS
SELECT 
    t.name as team_name,
    COUNT(DISTINCT tm.user_id) as total_members,
    COUNT(DISTINCT CASE WHEN tm.is_active = true THEN tm.user_id END) as active_members,
    COUNT(DISTINCT a.id) as total_assignments,
    COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.id END) as completed_assignments,
    ROUND(
        COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.id END) * 100.0 / 
        NULLIF(COUNT(DISTINCT a.id), 0), 2
    ) as completion_rate,
    AVG(CASE WHEN a.status = 'completed' AND a.actual_start_time IS NOT NULL AND a.actual_end_time IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (a.actual_end_time - a.actual_start_time)) / 3600 END) as avg_shift_hours
FROM tps_teams t
LEFT JOIN tps_team_memberships tm ON t.id = tm.team_id
LEFT JOIN tps_assignments a ON tm.user_id = a.user_id
WHERE t.is_active = true
GROUP BY t.id, t.name
ORDER BY completion_rate DESC;

-- =================================
-- MAINTENANCE PROCEDURES
-- =================================

-- Procedure to analyze table statistics (PostgreSQL)
CREATE OR REPLACE FUNCTION analyze_tps_tables() RETURNS void AS $$
BEGIN
    ANALYZE tps_users;
    ANALYZE tps_teams;
    ANALYZE tps_team_memberships;
    ANALYZE tps_shift_instances;
    ANALYZE tps_assignments;
    ANALYZE tps_user_skills;
    ANALYZE tps_swap_requests;
    ANALYZE tps_notifications;
    RAISE NOTICE 'TPS table statistics updated successfully';
END;
$$ LANGUAGE plpgsql;

-- Procedure to clean up expired data
CREATE OR REPLACE FUNCTION cleanup_expired_data() RETURNS void AS $$
BEGIN
    -- Mark expired swap requests
    UPDATE tps_swap_requests 
    SET status = 'expired' 
    WHERE status = 'pending' AND expires_at < NOW();
    
    -- Clean up old notification queue entries (older than 30 days)
    DELETE FROM tps_notification_queue 
    WHERE created_at < NOW() - INTERVAL '30 days' AND status = 'sent';
    
    -- Archive old assignment history (older than 2 years)
    -- This would typically move to an archive table in production
    -- DELETE FROM tps_assignment_history WHERE timestamp < NOW() - INTERVAL '2 years';
    
    RAISE NOTICE 'Expired data cleanup completed';
END;
$$ LANGUAGE plpgsql;

-- =================================
-- PERFORMANCE MONITORING
-- =================================

-- Function to get slow queries (PostgreSQL with pg_stat_statements)
CREATE OR REPLACE FUNCTION get_tps_slow_queries(min_duration_ms INTEGER DEFAULT 1000) 
RETURNS TABLE(
    query TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    max_time DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pss.query,
        pss.calls,
        pss.total_exec_time as total_time,
        pss.mean_exec_time as mean_time,
        pss.max_exec_time as max_time
    FROM pg_stat_statements pss
    WHERE pss.query LIKE '%tps_%'
    AND pss.mean_exec_time > min_duration_ms
    ORDER BY pss.mean_exec_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;