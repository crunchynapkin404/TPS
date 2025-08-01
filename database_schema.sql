-- TPS Monthly Timeline Shift Scheduler Database Schema
-- SQLite Database for FastAPI Backend

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Users/Employees table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    avatar_url VARCHAR(255),
    department VARCHAR(100),
    role VARCHAR(50) DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shift types/categories table
CREATE TABLE shift_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280', -- Hex color code
    duration_hours DECIMAL(4,2) DEFAULT 8.00,
    requires_handover BOOLEAN DEFAULT FALSE,
    max_per_day INTEGER DEFAULT 1,
    overtime_threshold DECIMAL(4,2) DEFAULT 8.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shifts table - main shift instances
CREATE TABLE shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    shift_type_id INTEGER NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    duration_hours DECIMAL(4,2) NOT NULL,
    is_overtime BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'scheduled', -- scheduled, confirmed, cancelled, completed
    notes TEXT,
    template_id INTEGER, -- Reference to shift template if created from template
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (shift_type_id) REFERENCES shift_types(id) ON DELETE RESTRICT,
    FOREIGN KEY (template_id) REFERENCES shift_templates(id) ON DELETE SET NULL
);

-- Shift templates for recurring patterns
CREATE TABLE shift_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    shift_type_id INTEGER NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    duration_hours DECIMAL(4,2) NOT NULL,
    days_of_week VARCHAR(20), -- JSON array like "[1,2,3,4,5]" for Mon-Fri
    recurrence_pattern VARCHAR(20) DEFAULT 'none', -- none, daily, weekly, monthly
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (shift_type_id) REFERENCES shift_types(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Shift conflicts tracking
CREATE TABLE shift_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id_1 INTEGER NOT NULL,
    shift_id_2 INTEGER NOT NULL,
    conflict_type VARCHAR(50) NOT NULL, -- overlap, double_booking, overtime_limit
    severity VARCHAR(20) DEFAULT 'warning', -- info, warning, error
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (shift_id_1) REFERENCES shifts(id) ON DELETE CASCADE,
    FOREIGN KEY (shift_id_2) REFERENCES shifts(id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Shift history for undo/redo functionality
CREATE TABLE shift_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id INTEGER,
    action VARCHAR(20) NOT NULL, -- create, update, delete, move, resize
    old_data TEXT, -- JSON of previous state
    new_data TEXT, -- JSON of new state
    user_id INTEGER,
    session_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Coverage requirements table
CREATE TABLE coverage_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    shift_type_id INTEGER NOT NULL,
    required_count INTEGER NOT NULL DEFAULT 1,
    min_coverage_hours DECIMAL(4,2) DEFAULT 8.00,
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, critical
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (shift_type_id) REFERENCES shift_types(id) ON DELETE CASCADE
);

-- User preferences and settings
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    preferred_shift_types TEXT, -- JSON array of preferred shift type IDs
    max_hours_per_week DECIMAL(4,2) DEFAULT 40.00,
    max_consecutive_days INTEGER DEFAULT 5,
    min_rest_hours DECIMAL(4,2) DEFAULT 11.00,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    calendar_view VARCHAR(20) DEFAULT 'month', -- week, month, year
    timezone VARCHAR(50) DEFAULT 'UTC',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_shifts_user_date ON shifts(user_id, date);
CREATE INDEX idx_shifts_date ON shifts(date);
CREATE INDEX idx_shifts_type ON shifts(shift_type_id);
CREATE INDEX idx_shifts_status ON shifts(status);
CREATE INDEX idx_shift_history_shift ON shift_history(shift_id);
CREATE INDEX idx_shift_history_session ON shift_history(session_id);
CREATE INDEX idx_coverage_date ON coverage_requirements(date);

-- Triggers for updated_at timestamps
CREATE TRIGGER update_users_timestamp 
    AFTER UPDATE ON users
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_shifts_timestamp 
    AFTER UPDATE ON shifts
    BEGIN
        UPDATE shifts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_user_preferences_timestamp 
    AFTER UPDATE ON user_preferences
    BEGIN
        UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Insert default shift types
INSERT INTO shift_types (name, display_name, description, color, duration_hours, requires_handover) VALUES
('morning', 'Morning Shift', 'Standard morning shift', '#3B82F6', 8.00, FALSE),
('afternoon', 'Afternoon Shift', 'Standard afternoon shift', '#10B981', 8.00, FALSE),
('evening', 'Evening Shift', 'Standard evening shift', '#F59E0B', 8.00, FALSE),
('night', 'Night Shift', 'Night shift with handover', '#8B5CF6', 12.00, TRUE),
('oncall', 'On-Call', 'On-call availability', '#EF4444', 24.00, FALSE),
('training', 'Training', 'Training session', '#6B7280', 4.00, FALSE),
('meeting', 'Meeting', 'Team meeting or briefing', '#EC4899', 2.00, FALSE),
('maintenance', 'Maintenance', 'System maintenance window', '#F97316', 4.00, FALSE);

-- Insert sample users for testing
INSERT INTO users (username, first_name, last_name, email, department, role) VALUES
('jdoe', 'John', 'Doe', 'john.doe@company.com', 'Operations', 'manager'),
('asmith', 'Alice', 'Smith', 'alice.smith@company.com', 'Operations', 'employee'),
('bwilson', 'Bob', 'Wilson', 'bob.wilson@company.com', 'Operations', 'employee'),
('cjohnson', 'Carol', 'Johnson', 'carol.johnson@company.com', 'Operations', 'employee'),
('dmiller', 'David', 'Miller', 'david.miller@company.com', 'Operations', 'employee'),
('ebrown', 'Emma', 'Brown', 'emma.brown@company.com', 'Operations', 'employee'),
('fgarcia', 'Frank', 'Garcia', 'frank.garcia@company.com', 'Operations', 'employee'),
('gwilliams', 'Grace', 'Williams', 'grace.williams@company.com', 'Operations', 'employee');

-- Insert default shift templates
INSERT INTO shift_templates (name, description, shift_type_id, start_time, end_time, duration_hours, days_of_week, recurrence_pattern) VALUES
('Standard Weekday Morning', 'Mon-Fri morning shifts', 1, '06:00', '14:00', 8.00, '[1,2,3,4,5]', 'weekly'),
('Standard Weekday Afternoon', 'Mon-Fri afternoon shifts', 2, '14:00', '22:00', 8.00, '[1,2,3,4,5]', 'weekly'),
('Weekend Coverage', 'Weekend shift coverage', 1, '08:00', '16:00', 8.00, '[6,7]', 'weekly'),
('Night Coverage', 'Nightly coverage shifts', 4, '22:00', '06:00', 8.00, '[1,2,3,4,5,6,7]', 'daily');

-- Insert user preferences for sample users
INSERT INTO user_preferences (user_id, preferred_shift_types, max_hours_per_week) VALUES
(1, '[1,2]', 40.00),
(2, '[1,3]', 40.00),
(3, '[2,4]', 45.00),
(4, '[1,2,3]', 40.00),
(5, '[4,5]', 50.00),
(6, '[1,2]', 35.00),
(7, '[2,3]', 40.00),
(8, '[1,4]', 42.00);