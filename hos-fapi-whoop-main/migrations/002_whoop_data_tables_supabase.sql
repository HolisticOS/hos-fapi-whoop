-- ============================================================================
-- WHOOP Data Storage Schema - Supabase Auth Integration
-- ============================================================================
-- This migration integrates WHOOP data with Supabase authentication
-- All tables use UUID user_id matching auth.users.id
-- Row Level Security (RLS) ensures users only see their own data
-- ============================================================================

-- ============================================================================
-- SYNC METADATA TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_sync_log_user_id ON whoop_sync_log(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sync_log_last_sync_at ON whoop_sync_log(last_sync_at);
CREATE INDEX IF NOT EXISTS idx_whoop_sync_log_data_type ON whoop_sync_log(data_type);

-- Row Level Security
ALTER TABLE whoop_sync_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sync logs"
ON whoop_sync_log FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage sync logs"
ON whoop_sync_log FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_sync_log IS 'Tracks last sync timestamp for each WHOOP data type per authenticated Supabase user';

-- ============================================================================
-- WHOOP USERS TABLE (OAuth Tokens)
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    whoop_user_id TEXT NOT NULL UNIQUE, -- WHOOP's user ID from their API
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[], -- Array of granted scopes
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_users_user_id ON whoop_users(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_users_whoop_user_id ON whoop_users(whoop_user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_users_is_active ON whoop_users(is_active);

-- Row Level Security
ALTER TABLE whoop_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own WHOOP connection"
ON whoop_users FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage WHOOP users"
ON whoop_users FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_users IS 'Links Supabase users to WHOOP accounts with OAuth tokens';

-- ============================================================================
-- WHOOP OAUTH STATES (Temporary)
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    state TEXT NOT NULL UNIQUE,
    code_verifier TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_user_id ON whoop_oauth_states(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_state ON whoop_oauth_states(state);
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_expires_at ON whoop_oauth_states(expires_at);

-- Row Level Security
ALTER TABLE whoop_oauth_states ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own OAuth states"
ON whoop_oauth_states FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage OAuth states"
ON whoop_oauth_states FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_oauth_states IS 'Temporary PKCE state storage for OAuth flow (expires after 10 minutes)';

-- ============================================================================
-- RECOVERY DATA TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_recovery (
    id TEXT PRIMARY KEY, -- WHOOP record ID (UUID from API)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Recovery metrics
    recovery_score INTEGER CHECK (recovery_score >= 0 AND recovery_score <= 100),
    hrv_rmssd_milli INTEGER CHECK (hrv_rmssd_milli >= 0),
    resting_heart_rate INTEGER CHECK (resting_heart_rate > 0 AND resting_heart_rate < 200),
    spo2_percentage NUMERIC(5,2) CHECK (spo2_percentage >= 0 AND spo2_percentage <= 100),
    skin_temp_celsius NUMERIC(5,2),

    -- Metadata
    calibration_state TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_user_id ON whoop_recovery(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_created_at ON whoop_recovery(created_at);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_user_date ON whoop_recovery(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_score ON whoop_recovery(recovery_score);

-- Row Level Security
ALTER TABLE whoop_recovery ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own recovery data"
ON whoop_recovery FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage recovery data"
ON whoop_recovery FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_recovery IS 'WHOOP daily recovery scores linked to Supabase authenticated users';

-- ============================================================================
-- SLEEP DATA TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_sleep (
    id TEXT PRIMARY KEY, -- WHOOP record ID
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Sleep metrics
    total_sleep_time_milli BIGINT CHECK (total_sleep_time_milli >= 0),
    sleep_performance_percentage INTEGER CHECK (sleep_performance_percentage >= 0 AND sleep_performance_percentage <= 100),
    sleep_consistency_percentage INTEGER CHECK (sleep_consistency_percentage >= 0 AND sleep_consistency_percentage <= 100),
    sleep_efficiency_percentage INTEGER CHECK (sleep_efficiency_percentage >= 0 AND sleep_efficiency_percentage <= 100),

    -- Sleep stages (milliseconds)
    rem_sleep_milli BIGINT CHECK (rem_sleep_milli >= 0),
    slow_wave_sleep_milli BIGINT CHECK (slow_wave_sleep_milli >= 0),
    light_sleep_milli BIGINT CHECK (light_sleep_milli >= 0),
    awake_milli BIGINT CHECK (awake_milli >= 0),

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,

    -- Reference
    cycle_id INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB,

    -- Constraint: end_time must be after start_time
    CHECK (end_time > start_time)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_user_id ON whoop_sleep(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_start_time ON whoop_sleep(start_time);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_end_time ON whoop_sleep(end_time);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_user_date ON whoop_sleep(user_id, end_time);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_performance ON whoop_sleep(sleep_performance_percentage);

-- Row Level Security
ALTER TABLE whoop_sleep ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sleep data"
ON whoop_sleep FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage sleep data"
ON whoop_sleep FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_sleep IS 'WHOOP sleep sessions linked to Supabase authenticated users';

-- ============================================================================
-- WORKOUT DATA TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_workout (
    id TEXT PRIMARY KEY, -- WHOOP record ID
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Workout metrics
    strain_score NUMERIC(5,2) CHECK (strain_score >= 0 AND strain_score <= 21),
    average_heart_rate INTEGER CHECK (average_heart_rate > 0 AND average_heart_rate < 250),
    max_heart_rate INTEGER CHECK (max_heart_rate > 0 AND max_heart_rate < 250),
    calories_burned NUMERIC(10,2) CHECK (calories_burned >= 0), -- Kilojoules
    distance_meters NUMERIC(12,2) CHECK (distance_meters >= 0),

    -- Workout details
    sport_id INTEGER,
    sport_name TEXT,

    -- Timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_milli BIGINT CHECK (duration_milli >= 0),

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,

    -- Tracking
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),

    -- Raw data fallback
    raw_data JSONB,

    -- Constraint: end_time must be after start_time
    CHECK (end_time > start_time)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_workout_user_id ON whoop_workout(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_start_time ON whoop_workout(start_time);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_end_time ON whoop_workout(end_time);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_user_date ON whoop_workout(user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_sport_name ON whoop_workout(sport_name);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_strain ON whoop_workout(strain_score);

-- Row Level Security
ALTER TABLE whoop_workout ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workout data"
ON whoop_workout FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage workout data"
ON whoop_workout FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_workout IS 'WHOOP workout sessions linked to Supabase authenticated users';

-- ============================================================================
-- CYCLE DATA TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS whoop_cycle (
    id TEXT PRIMARY KEY, -- WHOOP record ID
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Cycle metrics
    day_strain NUMERIC(5,2) CHECK (day_strain >= 0 AND day_strain <= 21),
    calories_burned INTEGER CHECK (calories_burned >= 0), -- Kilojoules
    average_heart_rate INTEGER CHECK (average_heart_rate > 0 AND average_heart_rate < 250),
    max_heart_rate INTEGER CHECK (max_heart_rate > 0 AND max_heart_rate < 250),

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
    raw_data JSONB,

    -- Constraint: end_time must be after start_time
    CHECK (end_time > start_time)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_user_id ON whoop_cycle(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_start_time ON whoop_cycle(start_time);
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_end_time ON whoop_cycle(end_time);
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_user_date ON whoop_cycle(user_id, start_time);
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_day_strain ON whoop_cycle(day_strain);

-- Row Level Security
ALTER TABLE whoop_cycle ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own cycle data"
ON whoop_cycle FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage cycle data"
ON whoop_cycle FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_cycle IS 'WHOOP daily cycles linked to Supabase authenticated users';

-- ============================================================================
-- HELPER FUNCTIONS (Updated for UUID)
-- ============================================================================

-- Function to get latest recovery for a user on a specific date
CREATE OR REPLACE FUNCTION get_latest_recovery(p_user_id UUID, p_date DATE)
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
      AND DATE(r.created_at AT TIME ZONE 'UTC') = p_date
    ORDER BY r.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get latest sleep for a user on a specific date
CREATE OR REPLACE FUNCTION get_latest_sleep(p_user_id UUID, p_date DATE)
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
      AND DATE(s.end_time AT TIME ZONE 'UTC') = p_date
    ORDER BY s.end_time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get daily summary for a user
CREATE OR REPLACE FUNCTION get_daily_summary(p_user_id UUID, p_date DATE)
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
        AND DATE(s.end_time AT TIME ZONE 'UTC') = p_date
    LEFT JOIN whoop_cycle c ON c.user_id = r.user_id
        AND DATE(c.start_time AT TIME ZONE 'UTC') = p_date
    WHERE r.user_id = p_user_id
      AND DATE(r.created_at AT TIME ZONE 'UTC') = p_date
    ORDER BY r.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update sync log (UUID version)
CREATE OR REPLACE FUNCTION update_sync_log(
    p_user_id UUID,
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user has WHOOP connected
CREATE OR REPLACE FUNCTION is_whoop_connected(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM whoop_users
        WHERE user_id = p_user_id AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's WHOOP connection status
CREATE OR REPLACE FUNCTION get_whoop_connection_info(p_user_id UUID)
RETURNS TABLE (
    is_connected BOOLEAN,
    whoop_user_id TEXT,
    last_sync TIMESTAMPTZ,
    scopes TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wu.is_active AS is_connected,
        wu.whoop_user_id,
        MAX(wsl.last_sync_at) AS last_sync,
        wu.scopes
    FROM whoop_users wu
    LEFT JOIN whoop_sync_log wsl ON wsl.user_id = wu.user_id
    WHERE wu.user_id = p_user_id
    GROUP BY wu.is_active, wu.whoop_user_id, wu.scopes;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- CLEANUP FUNCTION
-- ============================================================================

-- Function to cleanup expired OAuth states (runs periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_states()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM whoop_oauth_states WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables were created
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'whoop_%'
ORDER BY table_name;

-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'whoop_%'
ORDER BY tablename;

-- Verify indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'whoop_%'
ORDER BY tablename, indexname;

-- ============================================================================
-- COMMENTS & DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN whoop_sync_log.user_id IS 'References auth.users(id) - Supabase authenticated user';
COMMENT ON COLUMN whoop_users.user_id IS 'References auth.users(id) - Supabase authenticated user';
COMMENT ON COLUMN whoop_users.whoop_user_id IS 'WHOOP user ID from their API (different from Supabase ID)';
COMMENT ON COLUMN whoop_recovery.user_id IS 'References auth.users(id) - Supabase authenticated user';
COMMENT ON COLUMN whoop_sleep.user_id IS 'References auth.users(id) - Supabase authenticated user';
COMMENT ON COLUMN whoop_workout.user_id IS 'References auth.users(id) - Supabase authenticated user';
COMMENT ON COLUMN whoop_cycle.user_id IS 'References auth.users(id) - Supabase authenticated user';
