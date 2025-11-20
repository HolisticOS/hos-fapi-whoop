-- ============================================================================
-- Fix Cycle End Time - Allow NULL for In-Progress Cycles
-- ============================================================================
-- WHOOP cycles that are still in progress don't have an end_time yet
-- This migration makes end_time nullable to support in-progress cycles
--
-- Run this in Supabase SQL Editor:
-- 1. Go to Supabase Dashboard → SQL Editor
-- 2. Copy and paste this entire file
-- 3. Click Run
-- ============================================================================

-- Make end_time nullable in whoop_cycle table
ALTER TABLE whoop_cycle
ALTER COLUMN end_time DROP NOT NULL;

-- Update the check constraint to allow null end_time
-- (end_time must be after start_time, but can be NULL for in-progress cycles)
ALTER TABLE whoop_cycle
DROP CONSTRAINT IF EXISTS whoop_cycle_check;

ALTER TABLE whoop_cycle
ADD CONSTRAINT whoop_cycle_check
CHECK (end_time IS NULL OR end_time > start_time);

-- Add comment to explain nullable end_time
COMMENT ON COLUMN whoop_cycle.end_time IS 'Cycle end time (NULL for in-progress cycles that haven''t ended yet)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify the change
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'whoop_cycle'
  AND column_name IN ('start_time', 'end_time')
ORDER BY column_name;

-- Expected result:
-- column_name  | data_type                   | is_nullable | column_default
-- end_time     | timestamp with time zone    | YES         | NULL
-- start_time   | timestamp with time zone    | NO          | NULL

-- Check existing cycles with null end_time (should work after migration)
SELECT
    id,
    start_time,
    end_time,
    day_strain,
    CASE
        WHEN end_time IS NULL THEN 'In Progress'
        ELSE 'Completed'
    END as cycle_status
FROM whoop_cycle
WHERE end_time IS NULL
ORDER BY start_time DESC
LIMIT 5;

-- Test message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 004 completed successfully!';
    RAISE NOTICE 'Cycle end_time is now nullable to support in-progress cycles.';
END $$;
