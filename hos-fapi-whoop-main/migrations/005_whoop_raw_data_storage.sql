-- Migration: WHOOP Raw Data Storage (Simple JSON Approach)
-- This table stores all WHOOP data as raw JSON for maximum flexibility

-- Create the raw data storage table
CREATE TABLE IF NOT EXISTS whoop_raw_data (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL, -- Internal user ID (e.g., 'user002')
    whoop_user_id INTEGER, -- WHOOP's numeric user ID from API response  
    data_type TEXT NOT NULL, -- 'sleep', 'recovery', 'workout', 'cycle', 'profile'
    records JSONB NOT NULL, -- Raw WHOOP API response data
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    record_count INTEGER NOT NULL DEFAULT 0,
    next_token TEXT, -- For pagination
    api_endpoint TEXT, -- Source endpoint for debugging
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_user_id ON whoop_raw_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_type ON whoop_raw_data(data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_user_type ON whoop_raw_data(user_id, data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_fetched_at ON whoop_raw_data(fetched_at DESC);

-- JSONB indexes for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_records_gin ON whoop_raw_data USING GIN(records);

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_whoop_raw_data_updated_at 
    BEFORE UPDATE ON whoop_raw_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (Optional - enable if needed)
-- ALTER TABLE whoop_raw_data ENABLE ROW LEVEL SECURITY;

-- Example policies (uncomment if you want RLS)
-- CREATE POLICY "Users can view their own WHOOP data" 
--     ON whoop_raw_data FOR SELECT 
--     USING (auth.uid()::text = user_id);

-- CREATE POLICY "Service role can manage all WHOOP data" 
--     ON whoop_raw_data 
--     USING (auth.role() = 'service_role');

-- Example queries you can run:
/*
-- Get all sleep data for a user
SELECT records FROM whoop_raw_data 
WHERE user_id = 'user002' AND data_type = 'sleep'
ORDER BY fetched_at DESC LIMIT 1;

-- Get workout summaries
SELECT 
    records->0->>'sport_name' as sport,
    records->0->>'start' as workout_start,
    jsonb_array_length(records) as workout_count
FROM whoop_raw_data 
WHERE data_type = 'workout' AND user_id = 'user002';

-- Count total records by type
SELECT 
    data_type,
    SUM(record_count) as total_records,
    MAX(fetched_at) as last_updated
FROM whoop_raw_data 
WHERE user_id = 'user002'
GROUP BY data_type;
*/