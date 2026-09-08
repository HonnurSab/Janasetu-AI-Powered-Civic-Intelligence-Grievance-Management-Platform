CREATE TABLE IF NOT EXISTS citizens (
    citizen_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(32),
    address TEXT,
    district VARCHAR(120),
    ward VARCHAR(120),
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS departments (
    department_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(160) UNIQUE NOT NULL,
    category VARCHAR(160),
    district VARCHAR(120),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS officers (
    officer_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    department_id BIGINT NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    role VARCHAR(80) NOT NULL DEFAULT 'Department Officer',
    status VARCHAR(40) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('citizen','department','admin')),
    password_hash TEXT NOT NULL,
    citizen_id VARCHAR(32) UNIQUE REFERENCES citizens(citizen_id) ON DELETE CASCADE,
    officer_id BIGINT UNIQUE REFERENCES officers(officer_id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    CONSTRAINT users_role_identity CHECK (
      (role='citizen' AND citizen_id IS NOT NULL AND officer_id IS NULL) OR
      (role='department' AND officer_id IS NOT NULL AND citizen_id IS NULL) OR
      (role='admin' AND citizen_id IS NULL AND officer_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id VARCHAR(64) PRIMARY KEY,
    citizen_id VARCHAR(32) NOT NULL REFERENCES citizens(citizen_id) ON DELETE RESTRICT,
    complaint_text TEXT NOT NULL,
    original_language VARCHAR(10) NOT NULL DEFAULT 'en',
    translated_text TEXT,
    category VARCHAR(160) NOT NULL,
    priority VARCHAR(30) NOT NULL CHECK (priority IN ('Critical','High','Medium','Low')),
    status VARCHAR(40) NOT NULL CHECK (status IN ('New','Assigned','In Progress','Awaiting Verification','Resolved','Rejected')),
    department_id BIGINT NOT NULL REFERENCES departments(department_id) ON DELETE RESTRICT,
    assigned_to BIGINT REFERENCES officers(officer_id) ON DELETE SET NULL,
    district VARCHAR(120),
    ward VARCHAR(120),
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    sla_hours INTEGER NOT NULL DEFAULT 48,
    sla_deadline TIMESTAMPTZ,
    sla_breached BOOLEAN NOT NULL DEFAULT FALSE,
    ai_category_confidence DOUBLE PRECISION,
    location_source VARCHAR(30) DEFAULT 'manual',
    resolution_text TEXT,
    resolution_action TEXT,
    resolution_remarks TEXT,
    resolution_by VARCHAR(120)
);

CREATE TABLE IF NOT EXISTS complaint_updates (
    update_id BIGSERIAL PRIMARY KEY,
    complaint_id VARCHAR(64) NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    officer_id BIGINT REFERENCES officers(officer_id) ON DELETE SET NULL,
    status VARCHAR(40),
    comment TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id BIGSERIAL PRIMARY KEY,
    complaint_id VARCHAR(64) NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    original_name TEXT,
    mime_type VARCHAR(160),
    file_size BIGINT,
    media_type VARCHAR(30),
    purpose VARCHAR(30) NOT NULL DEFAULT 'complaint',
    uploaded_by VARCHAR(64),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    captured_at TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION,
    width INTEGER,
    height INTEGER,
    validation_status VARCHAR(40) DEFAULT 'accepted',
    metadata_json TEXT,
    thumbnail_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_role VARCHAR(80) NOT NULL,
    user_id VARCHAR(64),
    action TEXT NOT NULL,
    complaint_id VARCHAR(64),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_complaints_citizen ON complaints(citizen_id);
CREATE INDEX IF NOT EXISTS idx_complaints_department ON complaints(department_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority);
CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_ward_category ON complaints(ward, category);

CREATE OR REPLACE FUNCTION update_complaint_timestamp() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS complaints_updated_at ON complaints;
CREATE TRIGGER complaints_updated_at BEFORE UPDATE ON complaints
FOR EACH ROW EXECUTE FUNCTION update_complaint_timestamp();
