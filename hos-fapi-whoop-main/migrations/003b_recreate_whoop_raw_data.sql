-- ============================================================================
-- Drop and Recreate whoop_raw_data Table
-- ============================================================================
-- Run this ONLY if you already ran migration 003 and got the wrong schema
-- This will DROP all existing raw data and recreate with correct schema
-- ============================================================================

-- Drop the incorrectly created table
DROP TABLE IF EXISTS whoop_raw_data CASCADE;

-- Drop related functions if they exist
DROP FUNCTION IF EXISTS update_whoop_raw_data_updated_at() CASCADE;

-- Recreate with correct schema matching raw_data_storage.py expectations
CREATE TABLE whoop_raw_data (
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
CREATE INDEX idx_whoop_raw_data_user_id ON whoop_raw_data(user_id);
CREATE INDEX idx_whoop_raw_data_data_type ON whoop_raw_data(data_type);
CREATE INDEX idx_whoop_raw_data_user_type ON whoop_raw_data(user_id, data_type);
CREATE INDEX idx_whoop_raw_data_fetched_at ON whoop_raw_data(fetched_at DESC);

-- JSONB index for efficient JSON queries
CREATE INDEX idx_whoop_raw_data_records_gin ON whoop_raw_data USING GIN(records);

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

-- Verify table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'whoop_raw_data'
ORDER BY ordinal_position;
