-- =====================================================
-- WHOOP API v2 Migration Schema
-- Date: August 2025
-- Purpose: Add UUID support for v2 API while preserving v1 data
-- =====================================================

-- =====================================================
-- STEP 1: Backup existing data (RUN FIRST!)
-- =====================================================
-- Create backup tables before migration
CREATE TABLE IF NOT EXISTS public.whoop_users_backup AS 
SELECT * FROM public.whoop_users;

CREATE TABLE IF NOT EXISTS public.whoop_data_backup AS 
SELECT * FROM public.whoop_data;

-- =====================================================
-- STEP 2: Modify whoop_users table for v2
-- =====================================================

-- Add v2 specific columns to whoop_users
ALTER TABLE public.whoop_users 
ADD COLUMN IF NOT EXISTS whoop_user_uuid UUID,
ADD COLUMN IF NOT EXISTS api_version TEXT DEFAULT 'v1',
ADD COLUMN IF NOT EXISTS migrated_to_v2 BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS v2_migration_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS v1_user_id_backup TEXT;

-- Store v1 ID as backup before migration
UPDATE public.whoop_users 
SET v1_user_id_backup = whoop_user_id 
WHERE v1_user_id_backup IS NULL;

-- =====================================================
-- STEP 3: Create enhanced whoop_data_v2 structure
-- =====================================================

-- Create new comprehensive data table for v2
CREATE TABLE IF NOT EXISTS public.whoop_data_v2 (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    
    -- Data type and identification
    data_type TEXT NOT NULL CHECK (data_type IN ('recovery', 'workout', 'cycle', 'sleep', 'body_measurement')),
    
    -- v2 UUID identifiers (primary)
    whoop_uuid TEXT,  -- The v2 UUID identifier
    
    -- v1 compatibility fields
    whoop_v1_id TEXT,  -- Original v1 integer ID preserved as text
    activity_v1_id INTEGER,  -- For sleep/workout backward compatibility
    
    -- Timestamps and dates
    record_date DATE NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Data storage
    raw_data JSONB NOT NULL,  -- Complete API response
    processed_data JSONB,      -- Normalized/processed version
    
    -- Sync tracking
    sync_date DATE DEFAULT CURRENT_DATE,
    sync_source TEXT DEFAULT 'v2',  -- 'v1', 'v2', 'migration'
    is_latest_for_date BOOLEAN DEFAULT TRUE,
    
    -- Migration tracking
    migrated_from_v1 BOOLEAN DEFAULT FALSE,
    migration_notes TEXT,
    
    -- Constraints
    CONSTRAINT unique_v2_record UNIQUE(user_id, data_type, whoop_uuid),
    CONSTRAINT unique_v1_record UNIQUE(user_id, data_type, whoop_v1_id)
);

-- =====================================================
-- STEP 4: Create specific tables for better performance
-- =====================================================

-- Sleep data with v2 UUID support
CREATE TABLE IF NOT EXISTS public.whoop_sleep_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    
    -- Identifiers
    sleep_uuid TEXT UNIQUE NOT NULL,  -- v2 UUID
    sleep_v1_id INTEGER,               -- v1 integer ID for compatibility
    cycle_id TEXT,                     -- Reference to cycle
    
    -- Sleep metrics
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    timezone_offset TEXT,
    
    -- Sleep stages (in milliseconds)
    total_sleep_time_milli INTEGER,
    time_in_bed_milli INTEGER,
    awake_time_milli INTEGER,
    light_sleep_milli INTEGER,
    slow_wave_sleep_milli INTEGER,
    rem_sleep_milli INTEGER,
    
    -- Sleep scores
    sleep_efficiency DECIMAL(5,2),
    sleep_consistency DECIMAL(5,2),
    sleep_performance_percentage DECIMAL(5,2),
    
    -- Additional metrics
    respiratory_rate DECIMAL(5,2),
    
    -- Metadata
    raw_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT unique_sleep_uuid UNIQUE(sleep_uuid),
    CONSTRAINT unique_sleep_v1 UNIQUE(user_id, sleep_v1_id)
);

-- Workout data with v2 UUID support
CREATE TABLE IF NOT EXISTS public.whoop_workout_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    
    -- Identifiers
    workout_uuid TEXT UNIQUE NOT NULL,  -- v2 UUID
    workout_v1_id INTEGER,               -- v1 integer ID for compatibility
    
    -- Workout details
    sport_id INTEGER NOT NULL,
    sport_name TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    timezone_offset TEXT,
    
    -- Performance metrics
    strain_score DECIMAL(5,2),
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    calories_burned INTEGER,
    distance_meters DECIMAL(10,2),
    
    -- Zone durations (milliseconds)
    zone_zero_milli INTEGER,
    zone_one_milli INTEGER,
    zone_two_milli INTEGER,
    zone_three_milli INTEGER,
    zone_four_milli INTEGER,
    zone_five_milli INTEGER,
    
    -- Metadata
    raw_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_workout_uuid UNIQUE(workout_uuid),
    CONSTRAINT unique_workout_v1 UNIQUE(user_id, workout_v1_id)
);

-- Recovery data (unchanged structure, but add v2 tracking)
CREATE TABLE IF NOT EXISTS public.whoop_recovery_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    
    -- Identifiers
    cycle_id TEXT UNIQUE NOT NULL,
    
    -- Recovery metrics
    recovery_score DECIMAL(5,2),
    hrv_rmssd DECIMAL(10,2),
    resting_heart_rate DECIMAL(5,2),
    respiratory_rate DECIMAL(5,2),
    
    -- Additional scores
    hrv_score DECIMAL(5,2),
    rhr_score DECIMAL(5,2),
    respiratory_score DECIMAL(5,2),
    
    -- Metadata
    recorded_at TIMESTAMPTZ NOT NULL,
    raw_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_recovery_cycle UNIQUE(user_id, cycle_id)
);

-- =====================================================
-- STEP 5: Create indexes for performance
-- =====================================================

-- Indexes for whoop_data_v2
CREATE INDEX idx_whoop_data_v2_user_type ON public.whoop_data_v2 (user_id, data_type);
CREATE INDEX idx_whoop_data_v2_uuid ON public.whoop_data_v2 (whoop_uuid);
CREATE INDEX idx_whoop_data_v2_v1_id ON public.whoop_data_v2 (whoop_v1_id);
CREATE INDEX idx_whoop_data_v2_record_date ON public.whoop_data_v2 (record_date DESC);
CREATE INDEX idx_whoop_data_v2_sync ON public.whoop_data_v2 (sync_date, sync_source);

-- Indexes for sleep
CREATE INDEX idx_sleep_v2_user ON public.whoop_sleep_v2 (user_id);
CREATE INDEX idx_sleep_v2_date ON public.whoop_sleep_v2 (start_time DESC);
CREATE INDEX idx_sleep_v2_cycle ON public.whoop_sleep_v2 (cycle_id);

-- Indexes for workout
CREATE INDEX idx_workout_v2_user ON public.whoop_workout_v2 (user_id);
CREATE INDEX idx_workout_v2_date ON public.whoop_workout_v2 (start_time DESC);
CREATE INDEX idx_workout_v2_sport ON public.whoop_workout_v2 (sport_id);

-- Indexes for recovery
CREATE INDEX idx_recovery_v2_user ON public.whoop_recovery_v2 (user_id);
CREATE INDEX idx_recovery_v2_date ON public.whoop_recovery_v2 (recorded_at DESC);

-- =====================================================
-- STEP 6: Create migration tracking table
-- =====================================================

CREATE TABLE IF NOT EXISTS public.whoop_migration_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    v1_id TEXT,
    v2_id TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- =====================================================
-- STEP 7: Create migration helper functions
-- =====================================================

-- Function to migrate v1 data to v2 format
CREATE OR REPLACE FUNCTION migrate_whoop_v1_to_v2(
    p_user_id UUID,
    p_data_type TEXT
) RETURNS INTEGER AS $$
DECLARE
    migrated_count INTEGER := 0;
    v1_record RECORD;
BEGIN
    -- Migrate existing v1 data to v2 structure
    FOR v1_record IN 
        SELECT * FROM public.whoop_data 
        WHERE user_id = p_user_id 
        AND data_type = p_data_type
    LOOP
        INSERT INTO public.whoop_data_v2 (
            user_id,
            data_type,
            whoop_v1_id,
            record_date,
            raw_data,
            processed_data,
            sync_source,
            migrated_from_v1
        ) VALUES (
            v1_record.user_id,
            v1_record.data_type,
            v1_record.whoop_record_id,
            v1_record.record_date,
            v1_record.raw_data,
            v1_record.processed_data,
            'migration',
            TRUE
        ) ON CONFLICT (user_id, data_type, whoop_v1_id) DO NOTHING;
        
        migrated_count := migrated_count + 1;
    END LOOP;
    
    RETURN migrated_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- STEP 8: Enable Row Level Security on new tables
-- =====================================================

ALTER TABLE public.whoop_data_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_sleep_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_workout_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_recovery_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_migration_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies for v2 tables
CREATE POLICY "Service role can access all v2 data" ON public.whoop_data_v2
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Users can access own v2 data" ON public.whoop_data_v2
    FOR ALL USING (
        user_id IN (SELECT id FROM public.whoop_users WHERE auth.uid()::text = whoop_user_id)
    );

-- =====================================================
-- STEP 9: Create views for backward compatibility
-- =====================================================

-- Unified view combining v1 and v2 data
CREATE OR REPLACE VIEW public.whoop_all_data AS
SELECT 
    'v2' as source,
    id,
    user_id,
    data_type,
    COALESCE(whoop_uuid, whoop_v1_id) as record_id,
    whoop_uuid,
    whoop_v1_id,
    record_date,
    raw_data,
    created_at
FROM public.whoop_data_v2
UNION ALL
SELECT 
    'v1' as source,
    id,
    user_id,
    data_type,
    whoop_record_id as record_id,
    NULL as whoop_uuid,
    whoop_record_id as whoop_v1_id,
    record_date,
    raw_data,
    created_at
FROM public.whoop_data
WHERE NOT EXISTS (
    SELECT 1 FROM public.whoop_data_v2 v2 
    WHERE v2.user_id = whoop_data.user_id 
    AND v2.whoop_v1_id = whoop_data.whoop_record_id
);

-- =====================================================
-- STEP 10: Grant permissions
-- =====================================================

GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- =====================================================
-- Migration complete!
-- Run verification query:
-- SELECT 
--     'whoop_data_v2' as table_name, 
--     COUNT(*) as record_count 
-- FROM whoop_data_v2
-- UNION ALL
-- SELECT 
--     'whoop_sleep_v2', 
--     COUNT(*) 
-- FROM whoop_sleep_v2
-- UNION ALL
-- SELECT 
--     'whoop_workout_v2', 
--     COUNT(*) 
-- FROM whoop_workout_v2;
-- =====================================================