DROP DATABASE IF EXISTS attendance_db;
CREATE DATABASE attendance_db;
USE attendance_db;

-- USERS
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    email_notifications BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    last_ip VARCHAR(50) NULL,
    theme VARCHAR(10) NOT NULL DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
    records_per_page INT NOT NULL DEFAULT 10,
    session_token VARCHAR(100),
    failed_login_attempts INT DEFAULT 0,
    locked_until DATETIME NULL
);

-- STUDENTS
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL
);

-- ATTENDANCE
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    date DATE NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('Present', 'Absent', 'Leave')),
    UNIQUE(student_id, date),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ROLES
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

-- PERMISSIONS
CREATE TABLE permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    permission_name VARCHAR(100) UNIQUE NOT NULL
);

-- ROLE PERMISSIONS
CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    UNIQUE KEY uniq_role_permission (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- USER ROLES
CREATE TABLE user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    UNIQUE KEY uniq_user_role (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- USER NOTIFICATION SETTINGS
CREATE TABLE user_notification_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    low_attendance BOOLEAN DEFAULT TRUE,
    password_change BOOLEAN DEFAULT TRUE,
    new_student BOOLEAN DEFAULT TRUE,
    attendance_saved BOOLEAN DEFAULT TRUE,
    system_alerts BOOLEAN DEFAULT TRUE,
    login_alerts BOOLEAN DEFAULT TRUE,
    attendance_updates BOOLEAN DEFAULT TRUE,
    role_changes BOOLEAN DEFAULT TRUE,
    account_locked BOOLEAN DEFAULT TRUE,
    backup_completed BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- LOGS
CREATE TABLE logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(255) NOT NULL,
    target_table VARCHAR(64) NULL,
    target_id INT NULL,
    ip_address VARCHAR(50),
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_logs_user_time ON logs (user_id, time);

-- SETTINGS
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_name VARCHAR(50) UNIQUE NOT NULL,
    setting_value VARCHAR(100) NOT NULL
);

-- NOTIFICATIONS
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message VARCHAR(255) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_user_read_time ON notifications (user_id, is_read, time);

-- INSERT ROLES
INSERT INTO roles (role_name) VALUES
('admin'),
('teacher');

-- INSERT PERMISSIONS
INSERT INTO permissions (permission_name) VALUES
('manage_students'),
('mark_attendance'),
('edit_old_attendance'),
('view_reports'),
('export_reports'),
('manage_users'),
('manage_roles'),
('manage_settings'),
('manage_backup_restore');

-- CREATE ADMIN USER
INSERT INTO users (username, password, email, email_notifications, theme, records_per_page)
VALUES (
    'admin',
    'scrypt:32768:8:1$o6gOAPGGRXvVIi0H$8ac8a7affda4c137360b5e2cb1657f87a96b35b86c10ada1ab4b7ebfdb9690103107dbeee9eda42d2f6378e2c41c50af6a6d6b896bccd05af3a1ff4a4a9dcf74',
    NULL,
    TRUE,
    'light',
    10
);

-- ASSIGN ADMIN ROLE
INSERT INTO user_roles (user_id, role_id)
SELECT id, 1 FROM users WHERE username='admin';

-- ADMIN GETS ALL PERMISSIONS
INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions;

-- DEFAULT NOTIFICATION SETTINGS FOR ADMIN
INSERT INTO user_notification_settings (user_id)
SELECT id FROM users WHERE username='admin';

-- DEFAULT SETTINGS
INSERT INTO settings (setting_name, setting_value) VALUES
('attendance_limit', '75'),
('system_name', 'AIM'),
('login_tagline', 'Track attendance without the clutter'),
('year', '2026-27'),
('teacher_calendar_policy', 'current_week_only'),
('semester_start_date', '2026-01-01'),
('semester_end_date', '2026-12-31'),
('backup_retention_days', '30'),
('max_login_attempts', '5'),
('login_lock_minutes', '15');

-- SAMPLE STUDENT DATA MOVED TO data/sample_students.csv
-- Import the CSV from the Students page to seed demo data.

-- INDEXES
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_student_id ON attendance(student_id);
CREATE INDEX idx_student_roll ON students(roll);
CREATE INDEX idx_logs_user ON logs(user_id);
CREATE INDEX idx_logs_user_time ON logs(user_id, time);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_user_read_time ON notifications(user_id, is_read, time);
CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_users_session_token ON users(session_token);
