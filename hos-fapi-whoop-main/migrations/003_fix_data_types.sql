-- ============================================================================
-- Fix Data Type Mismatches - Migration 003
-- ============================================================================
-- This migration fixes INTEGER columns that should be NUMERIC/TEXT
-- to match actual WHOOP API response data types
-- ============================================================================

-- ============================================================================
-- FIX RECOVERY TABLE
-- ============================================================================

-- Fix HRV field (can have decimal values)
ALTER TABLE whoop_recovery
ALTER COLUMN hrv_rmssd_milli TYPE NUMERIC(10,3);

-- Update constraint to allow decimal values
ALTER TABLE whoop_recovery
DROP CONSTRAINT IF EXISTS whoop_recovery_hrv_rmssd_milli_check;

ALTER TABLE whoop_recovery
ADD CONSTRAINT whoop_recovery_hrv_rmssd_milli_check
CHECK (hrv_rmssd_milli >= 0);

-- ============================================================================
-- FIX SLEEP TABLE
-- ============================================================================

-- Fix percentage fields (can have decimal values)
ALTER TABLE whoop_sleep
ALTER COLUMN sleep_performance_percentage TYPE NUMERIC(5,2);

ALTER TABLE whoop_sleep
ALTER COLUMN sleep_consistency_percentage TYPE NUMERIC(5,2);

ALTER TABLE whoop_sleep
ALTER COLUMN sleep_efficiency_percentage TYPE NUMERIC(5,2);

-- Update constraints to allow decimal values
ALTER TABLE whoop_sleep
DROP CONSTRAINT IF EXISTS whoop_sleep_sleep_performance_percentage_check;

ALTER TABLE whoop_sleep
ADD CONSTRAINT whoop_sleep_sleep_performance_percentage_check
CHECK (sleep_performance_percentage >= 0 AND sleep_performance_percentage <= 100);

ALTER TABLE whoop_sleep
DROP CONSTRAINT IF EXISTS whoop_sleep_sleep_consistency_percentage_check;

ALTER TABLE whoop_sleep
ADD CONSTRAINT whoop_sleep_sleep_consistency_percentage_check
CHECK (sleep_consistency_percentage >= 0 AND sleep_consistency_percentage <= 100);

ALTER TABLE whoop_sleep
DROP CONSTRAINT IF EXISTS whoop_sleep_sleep_efficiency_percentage_check;

ALTER TABLE whoop_sleep
ADD CONSTRAINT whoop_sleep_sleep_efficiency_percentage_check
CHECK (sleep_efficiency_percentage >= 0 AND sleep_efficiency_percentage <= 100);

-- Fix cycle_id (WHOOP uses string/text IDs for cycles)
ALTER TABLE whoop_sleep
ALTER COLUMN cycle_id TYPE TEXT;

-- ============================================================================
-- FIX CYCLE TABLE
-- ============================================================================

-- Fix calories_burned (WHOOP returns decimal kilojoules)
ALTER TABLE whoop_cycle
ALTER COLUMN calories_burned TYPE NUMERIC(10,2);

-- Update constraint to allow decimal values
ALTER TABLE whoop_cycle
DROP CONSTRAINT IF EXISTS whoop_cycle_calories_burned_check;

ALTER TABLE whoop_cycle
ADD CONSTRAINT whoop_cycle_calories_burned_check
CHECK (calories_burned >= 0);

-- ============================================================================
-- CREATE WHOOP_RAW_DATA TABLE
-- ============================================================================
-- This table stores raw JSON responses from WHOOP API for debugging/auditing
-- Matches the schema expected by app/services/raw_data_storage.py

CREATE TABLE IF NOT EXISTS whoop_raw_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- WHOOP API metadata
    whoop_user_id TEXT, -- WHOOP's user ID from their API
    data_type TEXT NOT NULL, -- 'recovery', 'sleep', 'workout', 'cycle'

    -- Raw JSON storage
    records JSONB NOT NULL, -- Complete WHOOP API response (array of records)
    record_count INTEGER NOT NULL DEFAULT 0,

    -- Pagination
    next_token TEXT, -- For paginated API responses

    -- Metadata
    api_endpoint TEXT, -- e.g., '/v1/activity/sleep'
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_user_id ON whoop_raw_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_data_type ON whoop_raw_data(data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_user_type ON whoop_raw_data(user_id, data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_fetched_at ON whoop_raw_data(fetched_at DESC);

-- JSONB index for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_records_gin ON whoop_raw_data USING GIN(records);

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_whoop_raw_data_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_whoop_raw_data_updated_at
    BEFORE UPDATE ON whoop_raw_data
    FOR EACH ROW EXECUTE FUNCTION update_whoop_raw_data_updated_at();

-- Row Level Security
ALTER TABLE whoop_raw_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own raw data"
ON whoop_raw_data FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage raw data"
ON whoop_raw_data FOR ALL
USING (auth.role() = 'service_role');

COMMENT ON TABLE whoop_raw_data IS 'Raw JSON responses from WHOOP API for debugging and data recovery';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column types were changed
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('whoop_recovery', 'whoop_sleep', 'whoop_cycle')
  AND column_name IN (
    'hrv_rmssd_milli',
    'sleep_performance_percentage',
    'sleep_consistency_percentage',
    'sleep_efficiency_percentage',
    'cycle_id',
    'calories_burned'
  )
ORDER BY table_name, column_name;

-- Verify whoop_raw_data table exists
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'whoop_raw_data';

-- ============================================================================
-- COMMENTS & DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN whoop_recovery.hrv_rmssd_milli IS 'Heart Rate Variability in milliseconds (can be decimal)';
COMMENT ON COLUMN whoop_sleep.sleep_performance_percentage IS 'Sleep performance percentage (can be decimal 0-100)';
COMMENT ON COLUMN whoop_sleep.sleep_consistency_percentage IS 'Sleep consistency percentage (can be decimal 0-100)';
COMMENT ON COLUMN whoop_sleep.sleep_efficiency_percentage IS 'Sleep efficiency percentage (can be decimal 0-100)';
COMMENT ON COLUMN whoop_sleep.cycle_id IS 'WHOOP cycle ID reference (text string from API)';
COMMENT ON COLUMN whoop_cycle.calories_burned IS 'Energy burned in kilojoules (decimal value)';
COMMENT ON COLUMN whoop_raw_data.raw_json IS 'Complete JSON response from WHOOP API';
