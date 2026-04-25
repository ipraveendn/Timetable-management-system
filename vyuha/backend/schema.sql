-- VYUHA Database Schema v2.0
-- Complete Multi-tenant SaaS with Full Role-Based Access Control

-- ============================================
-- CORE COLLEGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS colleges (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  code VARCHAR(20),
  address TEXT,
  contact_email VARCHAR(150),
  contact_phone VARCHAR(20),
  status VARCHAR(20) DEFAULT 'pending', -- pending, active, suspended
  approved_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- USERS TABLE (Complete Role-Based System)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) REFERENCES colleges(college_id) ON DELETE CASCADE,
  email VARCHAR(150) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(100) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'faculty', -- superadmin, admin, hod, faculty, coordinator
  department VARCHAR(100),
  employee_id VARCHAR(50),
  phone VARCHAR(20),
  avatar_url TEXT,
  status VARCHAR(20) DEFAULT 'active', -- active, inactive, suspended
  email_verified BOOLEAN DEFAULT FALSE,
  last_login TIMESTAMP WITH TIME ZONE,
  password_changed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- PENDING USER REGISTRATIONS (Signup Flow)
-- ============================================
CREATE TABLE IF NOT EXISTS pending_users (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) REFERENCES colleges(college_id),
  email VARCHAR(150) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(100) NOT NULL,
  requested_role VARCHAR(20) NOT NULL DEFAULT 'faculty',
  department VARCHAR(100),
  employee_id VARCHAR(50),
  phone VARCHAR(20),
  status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
  rejection_reason TEXT,
  approved_by INTEGER REFERENCES users(id),
  rejected_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  reviewed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- PASSWORD RESET TOKENS
-- ============================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id SERIAL PRIMARY KEY,
  email VARCHAR(150) NOT NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  used_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE;

-- ============================================
-- FACULTY TABLE (Enhanced with User Link)
-- ============================================
CREATE TABLE IF NOT EXISTS faculty (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  name VARCHAR(100) NOT NULL,
  employee_id VARCHAR(50) NOT NULL,
  email VARCHAR(150),
  phone VARCHAR(20),
  department VARCHAR(100) NOT NULL,
  subjects JSONB NOT NULL DEFAULT '[]',
  semesters JSONB NOT NULL DEFAULT '[1,2,3,4,5,6,7,8]',
  max_classes_per_day INT NOT NULL DEFAULT 5,
  available_days JSONB NOT NULL DEFAULT '["Mon","Tue","Wed","Thu","Fri"]',
  status VARCHAR(20) DEFAULT 'active', -- active, on_leave, inactive
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (college_id, employee_id)
);

-- ============================================
-- SUBJECTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS subjects (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  code VARCHAR(20),
  semester INT NOT NULL,
  classes_per_week INT NOT NULL DEFAULT 2,
  room_type_required VARCHAR(50) DEFAULT 'classroom',
  duration_minutes INT NOT NULL DEFAULT 60,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (college_id, name, semester)
);

-- ============================================
-- ROOMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS rooms (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  room_code VARCHAR(20) NOT NULL,
  room_name VARCHAR(100) NOT NULL,
  capacity INT NOT NULL,
  room_type VARCHAR(50) NOT NULL, -- classroom, lab, hall, workshop
  floor VARCHAR(10),
  building VARCHAR(100),
  available_days JSONB NOT NULL DEFAULT '["Mon","Tue","Wed","Thu","Fri","Sat"]',
  status VARCHAR(20) DEFAULT 'active',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (college_id, room_code)
);

-- ============================================
-- TIMETABLE SLOTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS timetable_slots (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  semester INT NOT NULL,
  day VARCHAR(10) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  faculty_id INT NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  room_id INT REFERENCES rooms(id) ON DELETE SET NULL,
  is_substituted BOOLEAN DEFAULT FALSE,
  is_locked BOOLEAN DEFAULT FALSE, -- Locked slots cannot be auto-modified
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (college_id, semester, day, start_time, faculty_id)
);

-- ============================================
-- LEAVE REQUESTS TABLE (Enhanced)
-- ============================================
CREATE TABLE IF NOT EXISTS leave_requests (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  faculty_id INT NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  leave_date DATE NOT NULL,
  end_date DATE,
  leave_type VARCHAR(50) NOT NULL, -- sick, personal, conference, vacation, emergency
  reason TEXT,
  status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, cancelled
  approved_by INTEGER REFERENCES users(id),
  rejected_by INTEGER REFERENCES users(id),
  auto_processed BOOLEAN DEFAULT FALSE, -- Was auto-handler involved?
  submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  reviewed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- SUBSTITUTIONS TABLE (Enhanced)
-- ============================================
CREATE TABLE IF NOT EXISTS substitutions (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  leave_request_id INT REFERENCES leave_requests(id) ON DELETE CASCADE,
  original_faculty_id INT NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  substitute_faculty_id INT NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
  timetable_slot_id INT NOT NULL REFERENCES timetable_slots(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  status VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, rejected, completed
  priority INT DEFAULT 1, -- 1=highest, 2=medium, 3=low
  auto_assigned BOOLEAN DEFAULT FALSE,
  confirmed_by INTEGER REFERENCES users(id),
  notified_original BOOLEAN DEFAULT FALSE,
  notified_substitute BOOLEAN DEFAULT FALSE,
  requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  confirmed_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL, -- leave_request, substitution, timetable, approval, system
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  data JSONB DEFAULT '{}',
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Backward-compat migration for older notifications table definitions
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'notifications_user_id_fkey'
  ) THEN
    ALTER TABLE notifications
      ADD CONSTRAINT notifications_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
  END IF;
END $$;

-- ============================================
-- AUDIT LOGS (Coordinator Tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id INTEGER,
  old_value JSONB,
  new_value JSONB,
  ip_address VARCHAR(45),
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- TIMETABLE VALIDATION LOGS
-- ============================================
CREATE TABLE IF NOT EXISTS timetable_validation_logs (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  validation_type VARCHAR(50) NOT NULL, -- load_balance, conflict, spread, quality
  issues_found JSONB DEFAULT '[]',
  auto_fixed BOOLEAN DEFAULT FALSE,
  fixed_slots JSONB DEFAULT '[]',
  score_before DECIMAL(5,2),
  score_after DECIMAL(5,2),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- FEATURE FLAGS (Per-College Settings)
-- ============================================
CREATE TABLE IF NOT EXISTS feature_flags (
  id SERIAL PRIMARY KEY,
  college_id VARCHAR(20) UNIQUE NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  saturday_enabled BOOLEAN DEFAULT TRUE,
  sunday_enabled BOOLEAN DEFAULT FALSE,
  break_after_3rd_period BOOLEAN DEFAULT TRUE,
  max_lectures_per_day INT DEFAULT 4,
  lab_sessions_enabled BOOLEAN DEFAULT TRUE,
  even_distribution BOOLEAN DEFAULT TRUE,
  ai_chat BOOLEAN DEFAULT TRUE,
  auto_substitution BOOLEAN DEFAULT TRUE,
  email_notifications BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- CHAT SESSIONS + MEMORY (Hybrid Memory)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_sessions (
  id VARCHAR(64) PRIMARY KEY,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255),
  last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL, -- user | assistant | system
  content TEXT NOT NULL,
  intent VARCHAR(40),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_memory_facts (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  college_id VARCHAR(20) NOT NULL REFERENCES colleges(college_id) ON DELETE CASCADE,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  fact_type VARCHAR(50) NOT NULL, -- substitution_context, preference, workflow
  fact_key VARCHAR(120) NOT NULL,
  fact_value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence DECIMAL(4,3) DEFAULT 0.8,
  expires_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(session_id, fact_key)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_users_college ON users(college_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_password_changed_at ON users(password_changed_at);
CREATE INDEX IF NOT EXISTS idx_pending_users_college ON pending_users(college_id);
CREATE INDEX IF NOT EXISTS idx_pending_users_status ON pending_users(status);
CREATE INDEX IF NOT EXISTS idx_password_reset_email ON password_reset_tokens(email);
CREATE INDEX IF NOT EXISTS idx_password_reset_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_password_reset_expires_at ON password_reset_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_faculty_college ON faculty(college_id);
CREATE INDEX IF NOT EXISTS idx_faculty_user ON faculty(user_id);
CREATE INDEX IF NOT EXISTS idx_subjects_college_semester ON subjects(college_id, semester);
CREATE INDEX IF NOT EXISTS idx_rooms_college ON rooms(college_id);
CREATE INDEX IF NOT EXISTS idx_timetable_college_semester ON timetable_slots(college_id, semester);
CREATE INDEX IF NOT EXISTS idx_timetable_faculty ON timetable_slots(faculty_id);
CREATE INDEX IF NOT EXISTS idx_timetable_room ON timetable_slots(room_id);
CREATE INDEX IF NOT EXISTS idx_timetable_day_time ON timetable_slots(day, start_time);
CREATE INDEX IF NOT EXISTS idx_leave_faculty_date ON leave_requests(faculty_id, leave_date);
CREATE INDEX IF NOT EXISTS idx_leave_status ON leave_requests(status);
CREATE INDEX IF NOT EXISTS idx_substitutions_date ON substitutions(date);
CREATE INDEX IF NOT EXISTS idx_substitutions_status ON substitutions(status);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_logs_college ON audit_logs(college_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_college_user ON chat_sessions(college_id, user_id, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_facts_session_updated ON chat_memory_facts(session_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_facts_expiry ON chat_memory_facts(expires_at);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Properly using Supabase auth context
-- ============================================
ALTER TABLE colleges ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE faculty ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetable_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE substitutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetable_validation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_memory_facts ENABLE ROW LEVEL SECURITY;

-- Helper function to get college_id from JWT claims
CREATE OR REPLACE FUNCTION public.college_id()
RETURNS TEXT AS $$
  SELECT (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'college_id')::TEXT
$$ LANGUAGE SQL STABLE;

-- Helper function to get user role from JWT claims
CREATE OR REPLACE FUNCTION public.role()
RETURNS TEXT AS $$
  SELECT (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')::TEXT
$$ LANGUAGE SQL STABLE;

-- Helper function to get user_id from JWT claims
CREATE OR REPLACE FUNCTION public.user_id()
RETURNS TEXT AS $$
  SELECT (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'user_id')::TEXT
$$ LANGUAGE SQL STABLE;

-- Colleges: Public can see active colleges; superadmin sees all
DROP POLICY IF EXISTS "Colleges public read" ON colleges;
CREATE POLICY "Colleges public read" ON colleges FOR SELECT 
  USING (status = 'active' OR public.role() = 'superadmin');

-- Colleges: Public can insert (request onboarding)
DROP POLICY IF EXISTS "Colleges public insert" ON colleges;
CREATE POLICY "Colleges public insert" ON colleges FOR INSERT WITH CHECK (true);

-- Users: College isolation - users can only see users in their college
DROP POLICY IF EXISTS "Users college isolation" ON users;
CREATE POLICY "Users college isolation" ON users FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Users: Users can update their own profile
DROP POLICY IF EXISTS "Users self update" ON users;
CREATE POLICY "Users self update" ON users FOR UPDATE USING (
  id::TEXT = public.user_id() OR public.role() IN ('admin', 'superadmin', 'hod')
);

-- Users: Allow public admin registration during onboarding
DROP POLICY IF EXISTS "Users public onboarding insert" ON users;
CREATE POLICY "Users public onboarding insert" ON users FOR INSERT WITH CHECK (
  role = 'admin' AND status = 'inactive'
);

-- Pending Users: Public can insert
DROP POLICY IF EXISTS "Pending users insert" ON pending_users;
CREATE POLICY "Pending users insert" ON pending_users FOR INSERT WITH CHECK (true);

-- Pending Users: College admin can see their college's pending users
DROP POLICY IF EXISTS "Pending users college view" ON pending_users;
CREATE POLICY "Pending users college view" ON pending_users FOR SELECT USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Faculty: College isolation
DROP POLICY IF EXISTS "Faculty college isolation" ON faculty;
CREATE POLICY "Faculty college isolation" ON faculty FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Subjects: College isolation
DROP POLICY IF EXISTS "Subjects college isolation" ON subjects;
CREATE POLICY "Subjects college isolation" ON subjects FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Rooms: College isolation
DROP POLICY IF EXISTS "Rooms college isolation" ON rooms;
CREATE POLICY "Rooms college isolation" ON rooms FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Timetable: College isolation
DROP POLICY IF EXISTS "Timetable college isolation" ON timetable_slots;
CREATE POLICY "Timetable college isolation" ON timetable_slots FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Leave Requests: College isolation + user can see their own
DROP POLICY IF EXISTS "Leave requests college isolation" ON leave_requests;
CREATE POLICY "Leave requests college isolation" ON leave_requests FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Substitutions: College isolation
DROP POLICY IF EXISTS "Substitutions college isolation" ON substitutions;
CREATE POLICY "Substitutions college isolation" ON substitutions FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Notifications: User can only see their own + admin can see all for college
DROP POLICY IF EXISTS "Notifications user isolation" ON notifications;
CREATE POLICY "Notifications user isolation" ON notifications FOR ALL USING (
  user_id::TEXT = public.user_id() OR 
  college_id = public.college_id() AND public.role() IN ('admin', 'hod') OR
  public.role() = 'superadmin'
);

-- Notifications: Allow system-generated notifications
DROP POLICY IF EXISTS "Notifications public insert" ON notifications;
CREATE POLICY "Notifications public insert" ON notifications FOR INSERT WITH CHECK (true);

-- Audit Logs: College isolation
DROP POLICY IF EXISTS "Audit logs college isolation" ON audit_logs;
CREATE POLICY "Audit logs college isolation" ON audit_logs FOR SELECT USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Feature Flags: College isolation
DROP POLICY IF EXISTS "Feature flags college isolation" ON feature_flags;
CREATE POLICY "Feature flags college isolation" ON feature_flags FOR ALL USING (
  college_id = public.college_id() OR public.role() = 'superadmin'
);

-- Chat sessions: user and college isolation
DROP POLICY IF EXISTS "Chat sessions isolation" ON chat_sessions;
CREATE POLICY "Chat sessions isolation" ON chat_sessions FOR ALL USING (
  college_id = public.college_id() AND (user_id::TEXT = public.user_id() OR public.role() IN ('admin', 'hod', 'superadmin'))
);

-- Chat messages: user and college isolation
DROP POLICY IF EXISTS "Chat messages isolation" ON chat_messages;
CREATE POLICY "Chat messages isolation" ON chat_messages FOR ALL USING (
  college_id = public.college_id() AND (user_id::TEXT = public.user_id() OR public.role() IN ('admin', 'hod', 'superadmin'))
);

-- Chat memory facts: user and college isolation
DROP POLICY IF EXISTS "Chat memory facts isolation" ON chat_memory_facts;
CREATE POLICY "Chat memory facts isolation" ON chat_memory_facts FOR ALL USING (
  college_id = public.college_id() AND (user_id::TEXT = public.user_id() OR public.role() IN ('admin', 'hod', 'superadmin'))
);

-- ============================================
-- NO DEFAULT DEMO DATA IN PRODUCTION
-- ============================================
-- Keep this schema seed-free for production readiness.
-- Create superadmin/college records explicitly via admin workflows.
