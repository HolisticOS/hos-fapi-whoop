-- Fix missing columns in whoop_users table
-- Run this in Supabase SQL Editor

-- Add missing columns to whoop_users table
ALTER TABLE public.whoop_users 
ADD COLUMN IF NOT EXISTS access_token text,
ADD COLUMN IF NOT EXISTS refresh_token text,
ADD COLUMN IF NOT EXISTS token_expires_at timestamptz,
ADD COLUMN IF NOT EXISTS scopes text,
ADD COLUMN IF NOT EXISTS user_id text;

-- Update user_id to match whoop_user_id for existing records (if any)
UPDATE public.whoop_users SET user_id = whoop_user_id WHERE user_id IS NULL;

-- Add constraints
ALTER TABLE public.whoop_users 
ADD CONSTRAINT IF NOT EXISTS whoop_users_user_id_unique UNIQUE (user_id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_whoop_users_user_id ON public.whoop_users (user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_users_access_token ON public.whoop_users (access_token);

-- Verify the table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'whoop_users' 
AND table_schema = 'public'
ORDER BY ordinal_position;