-- Whoop MVP Database Schema
-- Simplified schema focusing only on essential tables for MVP
-- Target: 4-week development timeline with minimal complexity

-- =============================================================================
-- WHOOP MVP DATABASE SCHEMA
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. USER CONNECTION MANAGEMENT
-- =============================================================================

-- Core user connections table
CREATE TABLE whoop_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL UNIQUE,     -- Maps to Sahha user_id for consistency
    whoop_user_id TEXT,               -- Whoop's internal user ID
    access_token TEXT,                -- OAuth access token (encrypted in production)
    refresh_token TEXT,               -- OAuth refresh token (encrypted in production)
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT,                      -- OAuth scopes granted
    is_active BOOLEAN DEFAULT true,   -- Connection status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_whoop_users_user_id ON whoop_users(user_id);
CREATE INDEX idx_whoop_users_active ON whoop_users(is_active) WHERE is_active = true;

-- =============================================================================
-- 2. RECOVERY DATA (Core Whoop Strength)
-- =============================================================================

-- Recovery data table - Whoop's primary value proposition
CREATE TABLE whoop_recovery_data (
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

-- Indexes for performance
CREATE INDEX idx_whoop_recovery_user_id ON whoop_recovery_data(user_id);
CREATE INDEX idx_whoop_recovery_user_date ON whoop_recovery_data(user_id, date);
CREATE INDEX idx_whoop_recovery_date ON whoop_recovery_data(date);

-- =============================================================================
-- 3. SLEEP DATA (Simplified)
-- =============================================================================

-- Sleep data table - essential sleep metrics only
CREATE TABLE whoop_sleep_data (
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

-- Indexes for performance
CREATE INDEX idx_whoop_sleep_user_id ON whoop_sleep_data(user_id);
CREATE INDEX idx_whoop_sleep_user_date ON whoop_sleep_data(user_id, date);
CREATE INDEX idx_whoop_sleep_date ON whoop_sleep_data(date);

-- =============================================================================
-- 4. WORKOUT DATA (Simplified)
-- =============================================================================

-- Workout data table - basic workout metrics
CREATE TABLE whoop_workout_data (
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

-- Indexes for performance
CREATE INDEX idx_whoop_workout_user_id ON whoop_workout_data(user_id);
CREATE INDEX idx_whoop_workout_user_date ON whoop_workout_data(user_id, date);
CREATE INDEX idx_whoop_workout_date ON whoop_workout_data(date);

-- =============================================================================
-- 5. SIMPLE SYNC TRACKING (MVP Only)
-- =============================================================================

-- Basic sync tracking to avoid duplicate API calls
CREATE TABLE whoop_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    data_type TEXT NOT NULL,          -- 'recovery', 'sleep', 'workout'
    sync_date DATE NOT NULL,          -- Date of data synced
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    records_synced INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',    -- 'success', 'partial', 'failed'
    
    -- Prevent duplicate sync attempts
    CONSTRAINT unique_whoop_sync_user_type_date UNIQUE(user_id, data_type, sync_date)
);

-- Index for checking last sync
CREATE INDEX idx_whoop_sync_user_type ON whoop_sync_log(user_id, data_type);

-- =============================================================================
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE whoop_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_recovery_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_sleep_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_workout_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE whoop_sync_log ENABLE ROW LEVEL SECURITY;

-- Service role policies (for internal API access)
-- Note: Replace 'service_role' with your actual service role name

-- Whoop users table policies
CREATE POLICY "Service can manage whoop_users" ON whoop_users
    FOR ALL USING (auth.role() = 'service_role');

-- Recovery data policies
CREATE POLICY "Service can manage whoop_recovery_data" ON whoop_recovery_data
    FOR ALL USING (auth.role() = 'service_role');

-- Sleep data policies
CREATE POLICY "Service can manage whoop_sleep_data" ON whoop_sleep_data
    FOR ALL USING (auth.role() = 'service_role');

-- Workout data policies
CREATE POLICY "Service can manage whoop_workout_data" ON whoop_workout_data
    FOR ALL USING (auth.role() = 'service_role');

-- Sync log policies
CREATE POLICY "Service can manage whoop_sync_log" ON whoop_sync_log
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- 7. HELPER FUNCTIONS FOR COMMON QUERIES
-- =============================================================================

-- Function to get user's latest recovery data
CREATE OR REPLACE FUNCTION get_latest_recovery(p_user_id TEXT, p_days_back INTEGER DEFAULT 1)
RETURNS TABLE (
    recovery_score DECIMAL(5,2),
    hrv_rmssd DECIMAL(8,2),
    resting_heart_rate INTEGER,
    skin_temp_celsius DECIMAL(4,1),
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
        r.date,
        r.recorded_at
    FROM whoop_recovery_data r
    WHERE r.user_id = p_user_id
      AND r.date >= CURRENT_DATE - INTERVAL '%s days' % p_days_back
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
    date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.sleep_score,
        s.duration_seconds,
        s.efficiency_percentage,
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
      AND sync_date = p_date;
    
    -- If no sync record or sync is older than 4 hours, need to sync
    RETURN (last_sync IS NULL OR last_sync < NOW() - INTERVAL '4 hours');
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 8. SAMPLE QUERIES FOR TESTING
-- =============================================================================

-- Test data insertion (for development)
/*
-- Insert test user
INSERT INTO whoop_users (user_id, whoop_user_id, is_active) 
VALUES ('test_user_123', 'whoop_12345', true);

-- Insert test recovery data
INSERT INTO whoop_recovery_data (user_id, recovery_score, hrv_rmssd, resting_heart_rate, date) 
VALUES ('test_user_123', 78.5, 42.3, 52, CURRENT_DATE);

-- Insert test sleep data
INSERT INTO whoop_sleep_data (user_id, sleep_score, duration_seconds, efficiency_percentage, date) 
VALUES ('test_user_123', 82.0, 28800, 87.5, CURRENT_DATE);

-- Test queries
SELECT * FROM get_latest_recovery('test_user_123');
SELECT * FROM get_sleep_data_range('test_user_123', CURRENT_DATE - INTERVAL '7 days', CURRENT_DATE);
SELECT needs_sync('test_user_123', 'recovery', CURRENT_DATE);
*/

-- =============================================================================
-- 9. MIGRATION NOTES
-- =============================================================================

/*
MIGRATION CHECKLIST:

1. Run this schema on clean Supabase database
2. Verify UUID extension is enabled
3. Test RLS policies with service role
4. Update connection string in microservice
5. Test helper functions work correctly
6. Verify indexes are created properly

SKIPPED FOR MVP (Future Enhancements):
- Webhook event tracking table
- Detailed audit logs
- Data correlation tables
- Advanced caching tables
- User preference tables
- Data analytics/aggregation tables

MVP DESIGN PRINCIPLES:
- Keep it simple - only essential tables
- Optimize for read performance with indexes
- Use date-based partitioning concept with date columns
- Simple unique constraints to prevent duplicates
- Helper functions for common queries
- RLS policies for security

PERFORMANCE CONSIDERATIONS:
- Primary indexes on user_id and date columns
- Unique constraints prevent duplicate API calls
- Helper functions reduce complex query logic
- Date columns enable efficient range queries

SECURITY CONSIDERATIONS:
- RLS policies restrict access to service role
- OAuth tokens should be encrypted in production
- All timestamps use timezone-aware types
- User IDs are text for flexibility with external systems
*/