-- =====================================================
-- WHOOP OAuth Tables Migration - FIXED VERSION
-- Date: August 2025
-- Purpose: Add tables for automated OAuth flow with proper RLS
-- =====================================================

BEGIN;

-- =====================================================
-- OAuth State Table (temporary storage during OAuth flow)
-- =====================================================

CREATE TABLE IF NOT EXISTS public.whoop_oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    state TEXT NOT NULL UNIQUE,
    code_verifier TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- Index for quick state lookup
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_state 
ON public.whoop_oauth_states(state);

-- Index for cleanup of expired states
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_expires_at 
ON public.whoop_oauth_states(expires_at);

-- =====================================================
-- Update whoop_users table for OAuth tokens
-- =====================================================

-- Add OAuth token columns if they don't exist
DO $$ 
BEGIN
    -- Add access_token column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'access_token'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN access_token TEXT;
    END IF;
    
    -- Add refresh_token column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'refresh_token'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN refresh_token TEXT;
    END IF;
    
    -- Add token_expires_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'token_expires_at'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN token_expires_at TIMESTAMPTZ;
    END IF;
    
    -- Add whoop_user_id column (unique identifier from OAuth)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'whoop_user_id'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN whoop_user_id TEXT;
    END IF;
    
    -- Add is_active column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Add timestamps
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'whoop_users' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE public.whoop_users ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- =====================================================
-- Add constraints and indexes
-- =====================================================

-- Make whoop_user_id unique (primary identifier for OAuth users)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'whoop_users' AND constraint_name = 'whoop_users_whoop_user_id_unique'
    ) THEN
        ALTER TABLE public.whoop_users 
        ADD CONSTRAINT whoop_users_whoop_user_id_unique UNIQUE (whoop_user_id);
    END IF;
END $$;

-- Index for quick user lookup
CREATE INDEX IF NOT EXISTS idx_whoop_users_whoop_user_id 
ON public.whoop_users(whoop_user_id);

-- Index for active users
CREATE INDEX IF NOT EXISTS idx_whoop_users_is_active 
ON public.whoop_users(is_active) WHERE is_active = TRUE;

-- Index for token expiry checks
CREATE INDEX IF NOT EXISTS idx_whoop_users_token_expires_at 
ON public.whoop_users(token_expires_at);

-- =====================================================
-- Create function to cleanup expired OAuth states
-- =====================================================

CREATE OR REPLACE FUNCTION cleanup_expired_oauth_states()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.whoop_oauth_states 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Create function to update updated_at timestamp
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_whoop_users_updated_at ON public.whoop_users;
CREATE TRIGGER update_whoop_users_updated_at
    BEFORE UPDATE ON public.whoop_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Row Level Security (RLS) Policies - SIMPLIFIED
-- =====================================================

-- Enable RLS on OAuth tables
ALTER TABLE public.whoop_oauth_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_users ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- OAuth States Table Policies (Service Role Only)
-- =====================================================

-- Service role can manage all OAuth states
CREATE POLICY "Service role can manage oauth states" ON public.whoop_oauth_states
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- Whoop Users Table Policies (Simplified)
-- =====================================================

-- Service role can manage all user data (for OAuth flows and API operations)
CREATE POLICY "Service role can manage whoop users" ON public.whoop_users
    FOR ALL USING (auth.role() = 'service_role');

-- Allow authenticated users to view their own data (if needed for frontend)
-- Note: This is optional since we're primarily using service role
CREATE POLICY "Users can view own profile" ON public.whoop_users
    FOR SELECT USING (
        auth.role() = 'authenticated' AND 
        whoop_user_id = current_setting('app.current_user_id', true)
    );

-- =====================================================
-- Enable RLS on v2 data tables (simplified policies)
-- =====================================================

-- Enable RLS on existing v2 tables
DO $$ 
BEGIN
    EXECUTE 'ALTER TABLE public.whoop_sleep_v2 ENABLE ROW LEVEL SECURITY';
EXCEPTION 
    WHEN undefined_table THEN NULL;
END $$;

DO $$ 
BEGIN
    EXECUTE 'ALTER TABLE public.whoop_workout_v2 ENABLE ROW LEVEL SECURITY';
EXCEPTION 
    WHEN undefined_table THEN NULL;
END $$;

DO $$ 
BEGIN
    EXECUTE 'ALTER TABLE public.whoop_recovery_v2 ENABLE ROW LEVEL SECURITY';
EXCEPTION 
    WHEN undefined_table THEN NULL;
END $$;

DO $$ 
BEGIN
    EXECUTE 'ALTER TABLE public.whoop_data_v2 ENABLE ROW LEVEL SECURITY';
EXCEPTION 
    WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- Service Role Policies for Data Tables
-- =====================================================

-- Service role can manage all data (this is what our API uses)
DO $$
BEGIN
    BEGIN
        CREATE POLICY "Service role can manage sleep data" ON public.whoop_sleep_v2
            FOR ALL USING (auth.role() = 'service_role');
    EXCEPTION 
        WHEN undefined_table THEN NULL;
        WHEN duplicate_object THEN NULL;
    END;
END $$;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Service role can manage recovery data" ON public.whoop_recovery_v2
            FOR ALL USING (auth.role() = 'service_role');
    EXCEPTION 
        WHEN undefined_table THEN NULL;
        WHEN duplicate_object THEN NULL;
    END;
END $$;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Service role can manage workout data" ON public.whoop_workout_v2
            FOR ALL USING (auth.role() = 'service_role');
    EXCEPTION 
        WHEN undefined_table THEN NULL;
        WHEN duplicate_object THEN NULL;
    END;
END $$;

DO $$
BEGIN
    BEGIN
        CREATE POLICY "Service role can manage whoop data" ON public.whoop_data_v2
            FOR ALL USING (auth.role() = 'service_role');
    EXCEPTION 
        WHEN undefined_table THEN NULL;
        WHEN duplicate_object THEN NULL;
    END;
END $$;

-- =====================================================
-- Optional: User-level data access policies
-- =====================================================

-- If you want users to access their own data via frontend:
-- Uncomment these policies and set app.current_user_id in your API calls

/*
DO $$
BEGIN
    BEGIN
        CREATE POLICY "Users can view own sleep data" ON public.whoop_sleep_v2
            FOR SELECT USING (
                user_id = current_setting('app.current_user_id', true)
            );
    EXCEPTION 
        WHEN undefined_table THEN NULL;
        WHEN duplicate_object THEN NULL;
    END;
END $$;
*/

COMMIT;

-- =====================================================
-- Migration Complete!
-- 
-- Summary:
-- - OAuth tables created with proper RLS
-- - Service role has full access (for API operations)
-- - User access policies are optional and commented out
-- - Type casting issues resolved by using service role primarily
-- - All data operations go through service role (secure)
-- =====================================================

-- Verification queries:
SELECT 'OAuth Tables Created' as status;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN ('whoop_oauth_states', 'whoop_users');