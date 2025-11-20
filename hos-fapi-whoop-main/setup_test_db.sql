-- Quick database setup for testing WHOOP API
-- Run this if you get database errors during testing

-- Create whoop_oauth_states table (temporary OAuth state storage)
CREATE TABLE IF NOT EXISTS whoop_oauth_states (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    state TEXT NOT NULL UNIQUE,
    code_verifier TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Create whoop_users table (user tokens storage)
CREATE TABLE IF NOT EXISTS whoop_users (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    whoop_user_id TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create whoop_raw_data table (stores complete API responses)
CREATE TABLE IF NOT EXISTS whoop_raw_data (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    records JSONB NOT NULL,
    api_endpoint TEXT,
    next_token TEXT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_user_id ON whoop_oauth_states(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_state ON whoop_oauth_states(state);
CREATE INDEX IF NOT EXISTS idx_whoop_oauth_states_expires_at ON whoop_oauth_states(expires_at);

CREATE INDEX IF NOT EXISTS idx_whoop_users_whoop_user_id ON whoop_users(whoop_user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_users_is_active ON whoop_users(is_active);

CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_user_id ON whoop_raw_data(user_id);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_data_type ON whoop_raw_data(data_type);
CREATE INDEX IF NOT EXISTS idx_whoop_raw_data_fetched_at ON whoop_raw_data(fetched_at);

-- Create a cleanup function for expired OAuth states (optional)
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_states()
RETURNS void AS $$
BEGIN
    DELETE FROM whoop_oauth_states WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE whoop_oauth_states IS 'Temporary storage for OAuth PKCE flow state (auto-expires after 10 minutes)';
COMMENT ON TABLE whoop_users IS 'WHOOP user authentication tokens with automatic refresh support';
COMMENT ON TABLE whoop_raw_data IS 'Complete WHOOP API responses stored as JSON for flexible processing';
