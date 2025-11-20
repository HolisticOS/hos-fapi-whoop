-- Fix numeric column types to match WHOOP API v2 response format
-- Issue: WHOOP API returns all numeric values as floats, but some DB columns are INTEGER

-- Migration: 003_fix_recovery_numeric_types
-- Date: 2025-11-20
-- Description: Change numeric columns to appropriate types

BEGIN;

-- recovery_score: percentage with decimals (0-100)
ALTER TABLE whoop_recovery
  ALTER COLUMN recovery_score TYPE DECIMAL(5,2);

-- Add comments for documentation
COMMENT ON COLUMN whoop_recovery.recovery_score IS 'Recovery score percentage (0-100) - DECIMAL to support values like 53.5';

-- Note: resting_heart_rate and spo2_percentage are now converted to INT in Python code
-- before insertion, so they can remain as INTEGER in the database

COMMIT;

-- Verification query (run after migration):
-- SELECT column_name, data_type, numeric_precision, numeric_scale
-- FROM information_schema.columns
-- WHERE table_name = 'whoop_recovery'
-- AND column_name IN ('recovery_score', 'resting_heart_rate', 'spo2_percentage')
-- ORDER BY column_name;
