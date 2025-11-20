-- WHOOP Data Storage Schema with Incremental Sync Support
-- This migration creates normalized tables for WHOOP health data
-- Run after: 001_initial_setup.sql (or setup_test_db.sql)

-- ============================================================================
-- SYNC METADATA TABLE
-- Tracks when each user was last synced for each data type
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_sync_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    data_type TEXT NOT NULL, -- 'recovery', 'sleep', 'workout', 'cycle'
    last_sync_at TIMESTAMPTZ NOT NULL,
    sync_status TEXT DEFAULT 'success', -- 'success', 'partial', 'failed'
    records_synced INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one row per user per data type
    UNIQUE(user_id, data_type)
);

CREATE INDEX idx_whoop_sync_log_user_id ON whoop_sync_log(user_id);
CREATE INDEX idx_whoop_sync_log_last_sync_at ON whoop_sync_log(last_sync_at);

COMMENT ON TABLE whoop_sync_log IS 'Tracks last sync timestamp for each WHOOP data type per user';

-- ============================================================================
-- RECOVERY DATA TABLE
-- Stores daily recovery scores and HRV data
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_recovery (
    id TEXT PRIMARY KEY, -- WHOOP record ID (UUID from API)
    user_id TEXT NOT NULL,

    -- Recovery metrics
    recovery_score INTEGER, -- 0-100
    hrv_rmssd_milli INTEGER, -- HRV in milliseconds
    resting_heart_rate INTEGER, -- BPM
    spo2_percentage NUMERIC(5,2), -- Blood oxygen %
    skin_temp_celsius NUMERIC(5,2), -- Skin temperature

    -- Metadata
    calibration_state TEXT, -- 'calibrating', 'calibrated'
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB
);

CREATE INDEX idx_whoop_recovery_user_id ON whoop_recovery(user_id);
CREATE INDEX idx_whoop_recovery_created_at ON whoop_recovery(created_at);
CREATE INDEX idx_whoop_recovery_recovery_score ON whoop_recovery(recovery_score);

COMMENT ON TABLE whoop_recovery IS 'WHOOP daily recovery scores with HRV and resting heart rate';

-- ============================================================================
-- SLEEP DATA TABLE
-- Stores sleep sessions with performance metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_sleep (
    id TEXT PRIMARY KEY, -- WHOOP record ID (UUID from API)
    user_id TEXT NOT NULL,

    -- Sleep metrics
    total_sleep_time_milli BIGINT, -- Total sleep duration in milliseconds
    sleep_performance_percentage INTEGER, -- 0-100 (need vs actual)
    sleep_consistency_percentage INTEGER, -- 0-100
    sleep_efficiency_percentage INTEGER, -- 0-100

    -- Sleep stages (milliseconds)
    rem_sleep_milli BIGINT,
    slow_wave_sleep_milli BIGINT,
    light_sleep_milli BIGINT,
    awake_milli BIGINT,

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,

    -- Reference
    cycle_id INTEGER, -- Link to daily cycle

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB
);

CREATE INDEX idx_whoop_sleep_user_id ON whoop_sleep(user_id);
CREATE INDEX idx_whoop_sleep_start_time ON whoop_sleep(start_time);
CREATE INDEX idx_whoop_sleep_end_time ON whoop_sleep(end_time);
CREATE INDEX idx_whoop_sleep_performance ON whoop_sleep(sleep_performance_percentage);

COMMENT ON TABLE whoop_sleep IS 'WHOOP sleep sessions with performance and stage breakdown';

-- ============================================================================
-- WORKOUT DATA TABLE
-- Stores individual workout/activity sessions
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_workout (
    id TEXT PRIMARY KEY, -- WHOOP record ID (UUID from API)
    user_id TEXT NOT NULL,

    -- Workout metrics
    strain_score NUMERIC(5,2), -- 0-21 scale
    average_heart_rate INTEGER, -- BPM
    max_heart_rate INTEGER, -- BPM
    calories_burned NUMERIC(10,2), -- Kilojoules from API
    distance_meters NUMERIC(12,2),

    -- Workout details
    sport_id INTEGER,
    sport_name TEXT,

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_milli BIGINT, -- Duration in milliseconds

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB
);

CREATE INDEX idx_whoop_workout_user_id ON whoop_workout(user_id);
CREATE INDEX idx_whoop_workout_start_time ON whoop_workout(start_time);
CREATE INDEX idx_whoop_workout_end_time ON whoop_workout(end_time);
CREATE INDEX idx_whoop_workout_sport_name ON whoop_workout(sport_name);
CREATE INDEX idx_whoop_workout_strain ON whoop_workout(strain_score);

COMMENT ON TABLE whoop_workout IS 'WHOOP workout sessions with strain and heart rate data';

-- ============================================================================
-- CYCLE DATA TABLE
-- Stores daily physiological cycles (24-hour periods)
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_cycle (
    id TEXT PRIMARY KEY, -- WHOOP record ID (UUID from API)
    user_id TEXT NOT NULL,

    -- Cycle metrics
    day_strain NUMERIC(5,2), -- 0-21 scale (cumulative daily strain)
    calories_burned INTEGER, -- Kilojoules from API
    average_heart_rate INTEGER, -- BPM
    max_heart_rate INTEGER, -- BPM

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB
);

CREATE INDEX idx_whoop_cycle_user_id ON whoop_cycle(user_id);
CREATE INDEX idx_whoop_cycle_start_time ON whoop_cycle(start_time);
CREATE INDEX idx_whoop_cycle_end_time ON whoop_cycle(end_time);
CREATE INDEX idx_whoop_cycle_day_strain ON whoop_cycle(day_strain);

COMMENT ON TABLE whoop_cycle IS 'WHOOP daily cycles (24-hour physiological periods) with strain data';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get latest recovery for a user on a specific date
CREATE OR REPLACE FUNCTION get_latest_recovery(p_user_id TEXT, p_date DATE)
RETURNS TABLE (
    id TEXT,
    recovery_score INTEGER,
    hrv_rmssd_milli INTEGER,
    resting_heart_rate INTEGER,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.recovery_score,
        r.hrv_rmssd_milli,
        r.resting_heart_rate,
        r.created_at
    FROM whoop_recovery r
    WHERE r.user_id = p_user_id
      AND DATE(r.created_at) = p_date
    ORDER BY r.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest sleep for a user on a specific date
CREATE OR REPLACE FUNCTION get_latest_sleep(p_user_id TEXT, p_date DATE)
RETURNS TABLE (
    id TEXT,
    total_sleep_time_milli BIGINT,
    sleep_performance_percentage INTEGER,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.total_sleep_time_milli,
        s.sleep_performance_percentage,
        s.start_time,
        s.end_time
    FROM whoop_sleep s
    WHERE s.user_id = p_user_id
      AND DATE(s.end_time) = p_date
    ORDER BY s.end_time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to get daily summary for a user
CREATE OR REPLACE FUNCTION get_daily_summary(p_user_id TEXT, p_date DATE)
RETURNS TABLE (
    recovery_score INTEGER,
    sleep_performance INTEGER,
    sleep_duration_hours NUMERIC,
    day_strain NUMERIC,
    total_calories INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.recovery_score,
        s.sleep_performance_percentage,
        ROUND((s.total_sleep_time_milli / 3600000.0)::NUMERIC, 2) AS sleep_duration_hours,
        c.day_strain,
        c.calories_burned
    FROM whoop_recovery r
    LEFT JOIN whoop_sleep s ON s.user_id = r.user_id
        AND DATE(s.end_time) = p_date
    LEFT JOIN whoop_cycle c ON c.user_id = r.user_id
        AND DATE(c.start_time) = p_date
    WHERE r.user_id = p_user_id
      AND DATE(r.created_at) = p_date
    ORDER BY r.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to update sync log
CREATE OR REPLACE FUNCTION update_sync_log(
    p_user_id TEXT,
    p_data_type TEXT,
    p_records_synced INTEGER,
    p_status TEXT DEFAULT 'success',
    p_error_message TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    INSERT INTO whoop_sync_log (user_id, data_type, last_sync_at, sync_status, records_synced, error_message, updated_at)
    VALUES (p_user_id, p_data_type, NOW(), p_status, p_records_synced, p_error_message, NOW())
    ON CONFLICT (user_id, data_type)
    DO UPDATE SET
        last_sync_at = NOW(),
        sync_status = p_status,
        records_synced = whoop_sync_log.records_synced + p_records_synced,
        error_message = p_error_message,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS (if using different database roles)
-- ============================================================================

-- Grant permissions to application role (adjust role name as needed)
-- GRANT SELECT, INSERT, UPDATE ON whoop_sync_log TO whoop_app_role;
-- GRANT SELECT, INSERT, UPDATE ON whoop_recovery TO whoop_app_role;
-- GRANT SELECT, INSERT, UPDATE ON whoop_sleep TO whoop_app_role;
-- GRANT SELECT, INSERT, UPDATE ON whoop_workout TO whoop_app_role;
-- GRANT SELECT, INSERT, UPDATE ON whoop_cycle TO whoop_app_role;

-- ============================================================================
-- COMMENTS & DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN whoop_recovery.id IS 'Unique WHOOP record ID (prevents duplicates)';
COMMENT ON COLUMN whoop_sleep.id IS 'Unique WHOOP record ID (prevents duplicates)';
COMMENT ON COLUMN whoop_workout.id IS 'Unique WHOOP record ID (prevents duplicates)';
COMMENT ON COLUMN whoop_cycle.id IS 'Unique WHOOP record ID (prevents duplicates)';

COMMENT ON COLUMN whoop_recovery.raw_data IS 'Complete API response for debugging/future fields';
COMMENT ON COLUMN whoop_sleep.raw_data IS 'Complete API response for debugging/future fields';
COMMENT ON COLUMN whoop_workout.raw_data IS 'Complete API response for debugging/future fields';
COMMENT ON COLUMN whoop_cycle.raw_data IS 'Complete API response for debugging/future fields';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'whoop_%'
ORDER BY table_name;

-- Verify indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'whoop_%'
ORDER BY tablename, indexname;
