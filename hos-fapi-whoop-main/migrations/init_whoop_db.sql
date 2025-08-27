-- Whoop MVP Database Schema Migration
-- This file creates the complete database schema for the hos-fapi-whoop-main microservice
-- Based on whoop-mvp-database-schema.sql with production-ready enhancements

-- Enable UUID generation extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. USER CONNECTION MANAGEMENT TABLE
-- =============================================================================

-- Core user connections table for OAuth token management
CREATE TABLE IF NOT EXISTS whoop_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL UNIQUE,     -- Maps to Sahha user_id for consistency
    whoop_user_id TEXT,               -- Whoop's internal user ID
    access_token TEXT,                -- OAuth access token (should be encrypted in production)
    refresh_token TEXT,               -- OAuth refresh token (should be encrypted in production)
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT,                      -- OAuth scopes granted (comma-separated)
    is_active BOOLEAN DEFAULT true,   -- Connection status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes for whoop_users
CREATE INDEX IF NOT EXISTS idx_whoop_users_user_id ON whoop_users(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_users_active ON whoop_users(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_whoop_users_token_expires ON whoop_users(token_expires_at) WHERE token_expires_at IS NOT NULL;

-- =============================================================================
-- 2. RECOVERY DATA TABLE
-- =============================================================================

-- Recovery data table - Whoop's primary value proposition
CREATE TABLE IF NOT EXISTS whoop_recovery_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,            -- Direct user reference for easy queries
    cycle_id TEXT,                    -- Whoop cycle identifier
    recovery_score DECIMAL(5,2),     -- 0-100 recovery score
    hrv_rmssd DECIMAL(8,2),          -- Heart rate variability (RMSSD)
    resting_heart_rate INTEGER,      -- RHR in BPM
    skin_temp_celsius DECIMAL(4,1),  -- Skin temperature
    respiratory_rate DECIMAL(4,1),   -- Breathing rate
    date DATE NOT NULL,              -- Local date for easy querying
    recorded_at TIMESTAMP WITH TIME ZONE, -- When measurement was taken
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint to prevent duplicates per user per date
    CONSTRAINT unique_whoop_recovery_user_date UNIQUE(user_id, date)
);

-- Performance indexes for recovery data
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_user_id ON whoop_recovery_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_user_date ON whoop_recovery_data(user_id, date);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_date ON whoop_recovery_data(date);

-- =============================================================================
-- 3. SLEEP DATA TABLE
-- =============================================================================

-- Sleep data table - essential sleep metrics only
CREATE TABLE IF NOT EXISTS whoop_sleep_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    sleep_id TEXT,                    -- Whoop sleep session ID
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,         -- Total sleep duration
    efficiency_percentage DECIMAL(5,2), -- Sleep efficiency (0-100)
    sleep_score DECIMAL(5,2),        -- Whoop sleep score (0-100)
    
    -- Simplified sleep stages (minutes)
    light_sleep_minutes INTEGER,
    rem_sleep_minutes INTEGER,
    deep_sleep_minutes INTEGER,
    awake_minutes INTEGER,
    
    date DATE NOT NULL,              -- Sleep date (local)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint to prevent duplicates
    CONSTRAINT unique_whoop_sleep_user_date UNIQUE(user_id, date)
);

-- Performance indexes for sleep data
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_user_id ON whoop_sleep_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_user_date ON whoop_sleep_data(user_id, date);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_date ON whoop_sleep_data(date);

-- =============================================================================
-- 4. WORKOUT DATA TABLE
-- =============================================================================

-- Workout data table - basic workout metrics
CREATE TABLE IF NOT EXISTS whoop_workout_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    workout_id TEXT,                  -- Whoop workout ID
    sport_name TEXT,                  -- Activity type
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,         -- Workout duration
    strain DECIMAL(4,1),             -- Whoop strain score (0-21)
    average_heart_rate INTEGER,      -- Average HR during workout
    max_heart_rate INTEGER,          -- Peak HR during workout
    calories INTEGER,                -- Calories burned
    kilojoules INTEGER,              -- Energy in kJ
    date DATE NOT NULL,              -- Workout date (local)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    
    -- Note: No unique constraint as users can have multiple workouts per day
);

-- Performance indexes for workout data
CREATE INDEX IF NOT EXISTS idx_whoop_workout_user_id ON whoop_workout_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_user_date ON whoop_workout_data(user_id, date);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_date ON whoop_workout_data(date);

-- =============================================================================
-- 5. SYNC TRACKING TABLE
-- =============================================================================

-- Basic sync tracking to avoid duplicate API calls
CREATE TABLE IF NOT EXISTS whoop_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    data_type TEXT NOT NULL,          -- 'recovery', 'sleep', 'workout'
    sync_date DATE NOT NULL,          -- Date of data synced
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    records_synced INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',    -- 'success', 'partial', 'failed'
    error_message TEXT,               -- Store error details for debugging
    
    -- Prevent duplicate sync attempts
    CONSTRAINT unique_whoop_sync_user_type_date UNIQUE(user_id, data_type, sync_date)
);

-- Index for checking last sync status
CREATE INDEX IF NOT EXISTS idx_whoop_sync_user_type ON whoop_sync_log(user_id, data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_sync_status ON whoop_sync_log(status, last_sync_at);

-- =============================================================================
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables for security
ALTER TABLE whoop_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_recovery_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_sleep_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_workout_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_sync_log ENABLE ROW LEVEL SECURITY;

-- Service role policies (for microservice access)
-- Note: Adjust these policies based on your authentication system

-- Whoop users table policies
CREATE POLICY IF NOT EXISTS "Service can manage whoop_users" ON whoop_users
    FOR ALL USING (true);  -- Simplified for microservice access

-- Recovery data policies
CREATE POLICY IF NOT EXISTS "Service can manage whoop_recovery_data" ON whoop_recovery_data
    FOR ALL USING (true);

-- Sleep data policies
CREATE POLICY IF NOT EXISTS "Service can manage whoop_sleep_data" ON whoop_sleep_data
    FOR ALL USING (true);

-- Workout data policies  
CREATE POLICY IF NOT EXISTS "Service can manage whoop_workout_data" ON whoop_workout_data
    FOR ALL USING (true);

-- Sync log policies
CREATE POLICY IF NOT EXISTS "Service can manage whoop_sync_log" ON whoop_sync_log
    FOR ALL USING (true);

-- =============================================================================
-- 7. HELPER FUNCTIONS FOR COMMON OPERATIONS
-- =============================================================================

-- Function to get user's latest recovery data
CREATE OR REPLACE FUNCTION get_latest_recovery(p_user_id TEXT, p_days_back INTEGER DEFAULT 1)
RETURNS TABLE (
    recovery_score DECIMAL(5,2),
    hrv_rmssd DECIMAL(8,2),
    resting_heart_rate INTEGER,
    skin_temp_celsius DECIMAL(4,1),
    respiratory_rate DECIMAL(4,1),
    date DATE,
    recorded_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.recovery_score,
        r.hrv_rmssd,
        r.resting_heart_rate,
        r.skin_temp_celsius,
        r.respiratory_rate,
        r.date,
        r.recorded_at
    FROM whoop_recovery_data r
    WHERE r.user_id = p_user_id
      AND r.date >= CURRENT_DATE - INTERVAL '%s days'
    ORDER BY r.date DESC, r.recorded_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get user's sleep data for a date range
CREATE OR REPLACE FUNCTION get_sleep_data_range(p_user_id TEXT, p_start_date DATE, p_end_date DATE)
RETURNS TABLE (
    sleep_score DECIMAL(5,2),
    duration_seconds INTEGER,
    efficiency_percentage DECIMAL(5,2),
    light_sleep_minutes INTEGER,
    rem_sleep_minutes INTEGER,
    deep_sleep_minutes INTEGER,
    date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.sleep_score,
        s.duration_seconds,
        s.efficiency_percentage,
        s.light_sleep_minutes,
        s.rem_sleep_minutes,
        s.deep_sleep_minutes,
        s.date
    FROM whoop_sleep_data s
    WHERE s.user_id = p_user_id
      AND s.date BETWEEN p_start_date AND p_end_date
    ORDER BY s.date DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user needs data sync
CREATE OR REPLACE FUNCTION needs_sync(p_user_id TEXT, p_data_type TEXT, p_date DATE DEFAULT CURRENT_DATE)
RETURNS BOOLEAN AS $$
DECLARE
    last_sync TIMESTAMP WITH TIME ZONE;
BEGIN
    SELECT last_sync_at INTO last_sync
    FROM whoop_sync_log
    WHERE user_id = p_user_id
      AND data_type = p_data_type
      AND sync_date = p_date
      AND status = 'success';
    
    -- If no successful sync record or sync is older than 4 hours, need to sync
    RETURN (last_sync IS NULL OR last_sync < NOW() - INTERVAL '4 hours');
END;
$$ LANGUAGE plpgsql;

-- Function to get user's workout summary for a date range
CREATE OR REPLACE FUNCTION get_workout_summary(p_user_id TEXT, p_start_date DATE, p_end_date DATE)
RETURNS TABLE (
    total_workouts BIGINT,
    total_strain DECIMAL,
    avg_strain DECIMAL(4,1),
    total_calories INTEGER,
    avg_heart_rate DECIMAL,
    total_duration_minutes INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_workouts,
        SUM(w.strain) as total_strain,
        AVG(w.strain) as avg_strain,
        SUM(w.calories) as total_calories,
        AVG(w.average_heart_rate) as avg_heart_rate,
        SUM(w.duration_seconds) / 60 as total_duration_minutes
    FROM whoop_workout_data w
    WHERE w.user_id = p_user_id
      AND w.date BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. DATABASE INITIALIZATION VALIDATION
-- =============================================================================

-- Simple validation to ensure schema was created successfully
DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
BEGIN
    -- Check if all main tables exist
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
      AND table_name IN ('whoop_users', 'whoop_recovery_data', 'whoop_sleep_data', 'whoop_workout_data', 'whoop_sync_log');
    
    -- Check if helper functions exist
    SELECT COUNT(*) INTO function_count
    FROM information_schema.routines
    WHERE routine_schema = 'public'
      AND routine_name IN ('get_latest_recovery', 'get_sleep_data_range', 'needs_sync', 'get_workout_summary');
    
    -- Log validation results
    RAISE NOTICE 'Database schema validation: Tables created: %, Functions created: %', table_count, function_count;
    
    IF table_count < 5 THEN
        RAISE EXCEPTION 'Database schema incomplete: Expected 5 tables, found %', table_count;
    END IF;
    
    IF function_count < 4 THEN
        RAISE EXCEPTION 'Database functions incomplete: Expected 4 functions, found %', function_count;
    END IF;
    
    RAISE NOTICE 'Whoop MVP database schema initialization completed successfully!';
END $$;