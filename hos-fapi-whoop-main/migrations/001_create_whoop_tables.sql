-- Migration: Create WHOOP User Tables
-- This migration creates all necessary tables for WHOOP data integration
-- Run this in Supabase SQL Editor or via database migration tool

-- WHOOP Users table
CREATE TABLE IF NOT EXISTS public.whoop_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    whoop_user_id text UNIQUE NOT NULL,
    email text UNIQUE,
    first_name text,
    last_name text,
    profile_pic_url text,
    country text,
    admin_division text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    last_sync_at timestamptz,
    is_active boolean DEFAULT true,
    
    -- Constraints
    CONSTRAINT whoop_users_whoop_user_id_length CHECK (char_length(whoop_user_id) > 0)
);

-- WHOOP OAuth tokens table
CREATE TABLE IF NOT EXISTS public.whoop_oauth_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    access_token text NOT NULL,
    refresh_token text,
    token_type text DEFAULT 'bearer',
    expires_at timestamptz,
    scope text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    -- Ensure one active token per user
    UNIQUE(user_id)
);

-- WHOOP Data table for storing raw API responses
CREATE TABLE IF NOT EXISTS public.whoop_data (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    data_type text NOT NULL, -- 'recovery', 'workout', 'cycle', 'sleep'
    whoop_record_id text, -- WHOOP's internal ID for the record
    raw_data jsonb NOT NULL,
    processed_data jsonb, -- Normalized/processed version
    record_date date NOT NULL,
    sync_date date DEFAULT CURRENT_DATE,
    is_latest_for_date boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    
    -- Prevent duplicates
    UNIQUE(user_id, data_type, whoop_record_id)
);

-- WHOOP Sync Jobs table for tracking synchronization
CREATE TABLE IF NOT EXISTS public.whoop_sync_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.whoop_users(id) ON DELETE CASCADE,
    job_type text NOT NULL, -- 'full', 'incremental', 'recovery_only', etc.
    status text NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    start_date date,
    end_date date,
    records_synced integer DEFAULT 0,
    errors_count integer DEFAULT 0,
    error_details jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz DEFAULT now(),
    
    -- Check constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CONSTRAINT valid_job_type CHECK (job_type IN ('full', 'incremental', 'recovery_only', 'workout_only', 'cycle_only', 'sleep_only'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_whoop_data_user_type ON public.whoop_data (user_id, data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_data_record_date ON public.whoop_data (record_date);
CREATE INDEX IF NOT EXISTS idx_whoop_data_sync_date ON public.whoop_data (sync_date);
CREATE INDEX IF NOT EXISTS idx_whoop_sync_jobs_user_status ON public.whoop_sync_jobs (user_id, status);
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_tokens_user_id ON public.whoop_oauth_tokens (user_id);

-- Enable Row Level Security
ALTER TABLE public.whoop_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_oauth_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whoop_sync_jobs ENABLE ROW LEVEL SECURITY;

-- RLS Policies (service role can access all, users can access own data)
-- Drop existing policies first, then create new ones
DO $$
BEGIN
    -- whoop_users policies
    DROP POLICY IF EXISTS "Service role can access all users" ON public.whoop_users;
    DROP POLICY IF EXISTS "Users can access own profile" ON public.whoop_users;
    
    CREATE POLICY "Service role can access all users" ON public.whoop_users
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    CREATE POLICY "Users can access own profile" ON public.whoop_users  
        FOR ALL USING (auth.uid()::text = whoop_user_id);

    -- whoop_oauth_tokens policies
    DROP POLICY IF EXISTS "Service role can access all tokens" ON public.whoop_oauth_tokens;
    DROP POLICY IF EXISTS "Users can access own tokens" ON public.whoop_oauth_tokens;
    
    CREATE POLICY "Service role can access all tokens" ON public.whoop_oauth_tokens
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    CREATE POLICY "Users can access own tokens" ON public.whoop_oauth_tokens
        FOR ALL USING (
            user_id IN (SELECT id FROM public.whoop_users WHERE auth.uid()::text = whoop_user_id)
        );

    -- whoop_data policies
    DROP POLICY IF EXISTS "Service role can access all data" ON public.whoop_data;
    DROP POLICY IF EXISTS "Users can access own data" ON public.whoop_data;
    
    CREATE POLICY "Service role can access all data" ON public.whoop_data
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    CREATE POLICY "Users can access own data" ON public.whoop_data
        FOR ALL USING (
            user_id IN (SELECT id FROM public.whoop_users WHERE auth.uid()::text = whoop_user_id)
        );

    -- whoop_sync_jobs policies
    DROP POLICY IF EXISTS "Service role can access all sync jobs" ON public.whoop_sync_jobs;
    DROP POLICY IF EXISTS "Users can access own sync jobs" ON public.whoop_sync_jobs;
    
    CREATE POLICY "Service role can access all sync jobs" ON public.whoop_sync_jobs
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    CREATE POLICY "Users can access own sync jobs" ON public.whoop_sync_jobs
        FOR ALL USING (
            user_id IN (SELECT id FROM public.whoop_users WHERE auth.uid()::text = whoop_user_id)
        );
END $$;

-- Updated_at triggers
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_whoop_users_updated_at' 
        AND tgrelid = 'public.whoop_users'::regclass
    ) THEN
        CREATE TRIGGER update_whoop_users_updated_at 
            BEFORE UPDATE ON public.whoop_users 
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_whoop_oauth_tokens_updated_at' 
        AND tgrelid = 'public.whoop_oauth_tokens'::regclass
    ) THEN
        CREATE TRIGGER update_whoop_oauth_tokens_updated_at 
            BEFORE UPDATE ON public.whoop_oauth_tokens 
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
    END IF;
END $$;

-- Insert some test data for development (optional)
INSERT INTO public.whoop_users (whoop_user_id, email, first_name, last_name, is_active)
VALUES ('test_user_123', 'test@example.com', 'Test', 'User', true)
ON CONFLICT (whoop_user_id) DO NOTHING;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;