-- Quick fix for database schema mismatch
-- Run this in Supabase SQL Editor to align the database with the code

-- Add missing user_id column (which should match whoop_user_id for simplicity)
ALTER TABLE public.whoop_users ADD COLUMN IF NOT EXISTS user_id text;

-- Update user_id to match whoop_user_id for existing records
UPDATE public.whoop_users SET user_id = whoop_user_id WHERE user_id IS NULL;

-- Make user_id NOT NULL and add unique constraint
ALTER TABLE public.whoop_users ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.whoop_users ADD CONSTRAINT whoop_users_user_id_unique UNIQUE (user_id);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_whoop_users_user_id ON public.whoop_users (user_id);

-- Verify the changes
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'whoop_users' 
AND table_schema = 'public'
ORDER BY ordinal_position;