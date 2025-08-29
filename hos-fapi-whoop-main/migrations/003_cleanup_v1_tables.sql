-- =====================================================
-- WHOOP v2 Database Cleanup Migration
-- Date: August 2025
-- Purpose: Remove unnecessary v1 tables and backup tables
-- =====================================================

-- WARNING: This will permanently delete v1 data and backup tables
-- Ensure v2 migration is complete and data is verified before running!

BEGIN;

-- =====================================================
-- STEP 1: Verify v2 tables exist and have data
-- =====================================================

-- Check if v2 tables have data before cleanup
-- SELECT COUNT(*) FROM public.whoop_sleep_v2;
-- SELECT COUNT(*) FROM public.whoop_workout_v2;
-- SELECT COUNT(*) FROM public.whoop_data_v2;

-- =====================================================
-- STEP 2: Drop unnecessary indexes on tables to be removed
-- =====================================================

-- Drop indexes on whoop_data table (if they exist)
DROP INDEX IF EXISTS idx_whoop_data_user_id;
DROP INDEX IF EXISTS idx_whoop_data_record_date;
DROP INDEX IF EXISTS idx_whoop_data_data_type;
DROP INDEX IF EXISTS idx_whoop_data_whoop_record_id;

RAISE NOTICE 'Dropped old indexes';

-- =====================================================
-- STEP 3: Remove backup tables (no longer needed)
-- =====================================================

DROP TABLE IF EXISTS public.whoop_data_backup CASCADE;
DROP TABLE IF EXISTS public.whoop_users_backup CASCADE;

RAISE NOTICE 'Removed backup tables';

-- =====================================================
-- STEP 4: Remove old v1 data table
-- =====================================================

-- Remove the old whoop_data table (v1 data)
DROP TABLE IF EXISTS public.whoop_data CASCADE;

RAISE NOTICE 'Removed v1 whoop_data table';

-- =====================================================
-- STEP 5: Remove redundant OAuth tokens table
-- =====================================================

-- Remove whoop_oauth_tokens if tokens are stored in whoop_users
-- (Check if your implementation uses this table)
DROP TABLE IF EXISTS public.whoop_oauth_tokens CASCADE;

RAISE NOTICE 'Removed redundant OAuth tokens table';

-- =====================================================
-- STEP 6: Clean up whoop_users table - remove v1 compatibility fields
-- =====================================================

-- Remove v1 compatibility fields from whoop_users table
ALTER TABLE public.whoop_users 
DROP COLUMN IF EXISTS v1_user_id_backup,
DROP COLUMN IF EXISTS migrated_to_v2,
DROP COLUMN IF EXISTS v2_migration_date;

-- Update api_version default to v2 and remove v1 option
ALTER TABLE public.whoop_users 
ALTER COLUMN api_version SET DEFAULT 'v2';

-- Update all existing users to v2
UPDATE public.whoop_users 
SET api_version = 'v2' 
WHERE api_version = 'v1' OR api_version IS NULL;

RAISE NOTICE 'Cleaned up whoop_users table';

-- =====================================================
-- STEP 7: Add constraints for v2-only operation
-- =====================================================

-- Ensure api_version can only be v2
ALTER TABLE public.whoop_users 
ADD CONSTRAINT whoop_users_api_version_check 
CHECK (api_version = 'v2');

-- Ensure whoop_user_uuid is present for all active users
-- (This may need to be populated during migration)
-- ALTER TABLE public.whoop_users 
-- ADD CONSTRAINT whoop_users_uuid_required 
-- CHECK (whoop_user_uuid IS NOT NULL OR is_active = FALSE);

RAISE NOTICE 'Added v2-only constraints';

-- =====================================================
-- STEP 8: Update whoop_data_v2 to be the primary data table
-- =====================================================

-- Remove migration tracking fields from whoop_data_v2
ALTER TABLE public.whoop_data_v2 
DROP COLUMN IF EXISTS migrated_from_v1,
DROP COLUMN IF EXISTS migration_notes;

-- Update sync_source default to just 'api'
ALTER TABLE public.whoop_data_v2 
ALTER COLUMN sync_source SET DEFAULT 'api';

-- Update existing records
UPDATE public.whoop_data_v2 
SET sync_source = 'api' 
WHERE sync_source IN ('v1', 'v2', 'migration');

RAISE NOTICE 'Cleaned up whoop_data_v2 table';

-- =====================================================
-- STEP 9: Clean up migration log (keep for audit)
-- =====================================================

-- Keep migration log but mark old migrations as archived
UPDATE public.whoop_migration_log 
SET status = 'archived' 
WHERE migration_type IN ('v1_to_v2', 'data_migration') 
AND status = 'completed';

RAISE NOTICE 'Archived completed migration logs';

-- =====================================================
-- STEP 10: Optimize remaining tables
-- =====================================================

-- Analyze tables for better query planning
ANALYZE public.whoop_users;
ANALYZE public.whoop_data_v2;
ANALYZE public.whoop_sleep_v2;
ANALYZE public.whoop_workout_v2;
ANALYZE public.whoop_recovery_v2;

RAISE NOTICE 'Optimized remaining tables';

-- =====================================================
-- STEP 11: Create summary view (optional)
-- =====================================================

-- Create a summary view for monitoring
CREATE OR REPLACE VIEW public.whoop_data_summary AS
SELECT 
    'users' as table_name,
    COUNT(*) as record_count,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count
FROM public.whoop_users
UNION ALL
SELECT 
    'sleep_v2',
    COUNT(*),
    COUNT(CASE WHEN created_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 END)
FROM public.whoop_sleep_v2
UNION ALL
SELECT 
    'workout_v2',
    COUNT(*),
    COUNT(CASE WHEN created_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 END)
FROM public.whoop_workout_v2
UNION ALL
SELECT 
    'recovery_v2',
    COUNT(*),
    COUNT(CASE WHEN created_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 END)
FROM public.whoop_recovery_v2
UNION ALL
SELECT 
    'data_v2',
    COUNT(*),
    COUNT(CASE WHEN created_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 END)
FROM public.whoop_data_v2;

RAISE NOTICE 'Created data summary view';

COMMIT;

-- =====================================================
-- Cleanup Complete!
-- 
-- Summary of changes:
-- - Removed: whoop_data, whoop_data_backup, whoop_users_backup, whoop_oauth_tokens
-- - Cleaned: whoop_users (removed v1 compatibility fields)
-- - Updated: All references to use v2 only
-- - Added: v2-only constraints
-- - Created: Summary view for monitoring
-- =====================================================

RAISE NOTICE '=== WHOOP v2 Database Cleanup Complete! ===';
RAISE NOTICE 'Remaining tables: whoop_users, whoop_data_v2, whoop_sleep_v2, whoop_workout_v2, whoop_recovery_v2, whoop_sync_jobs, whoop_migration_log';
RAISE NOTICE 'All tables are now optimized for v2-only operation';

-- Verification query - run this after the migration
DO $$
BEGIN
    RAISE NOTICE 'Final table counts:';
    RAISE NOTICE '- whoop_users: %', (SELECT COUNT(*) FROM public.whoop_users);
    RAISE NOTICE '- whoop_sleep_v2: %', (SELECT COUNT(*) FROM public.whoop_sleep_v2);
    RAISE NOTICE '- whoop_workout_v2: %', (SELECT COUNT(*) FROM public.whoop_workout_v2);
    RAISE NOTICE '- whoop_recovery_v2: %', (SELECT COUNT(*) FROM public.whoop_recovery_v2);
    RAISE NOTICE '- whoop_data_v2: %', (SELECT COUNT(*) FROM public.whoop_data_v2);
    RAISE NOTICE '- whoop_sync_jobs: %', (SELECT COUNT(*) FROM public.whoop_sync_jobs);
END
$$;