# WHOOP Database Migrations

## Quick Fix for "Table not found" Error

You're seeing the PGRST205 error because the WHOOP database tables don't exist in your Supabase project yet.

### Option 1: Run SQL Migration (Recommended)

1. Go to your **Supabase Dashboard** → **SQL Editor**
2. Copy and paste the entire contents of `001_create_whoop_tables.sql`
3. Click **Run** to create all tables

### Option 2: Command Line (if you have Supabase CLI)

```bash
supabase db push
```

### What the Migration Creates

- `whoop_users` - User profile information
- `whoop_oauth_tokens` - OAuth 2.0 access tokens
- `whoop_data` - Raw and processed WHOOP data
- `whoop_sync_jobs` - Data synchronization tracking

### After Running Migration

Your application will start normally and the error will be resolved. You'll see:

```
INFO: Database initialized successfully
INFO: WHOOP Microservice started successfully
```

### Current Behavior (Without Migration)

The application runs in **degraded mode** - it starts successfully but database operations will fail. You'll see:

```
WARNING: Database tables missing - running in degraded mode
INFO: To fix: Run the SQL migration script in /migrations/001_create_whoop_tables.sql
```

### Verification

After running the migration, restart your application:

```bash
python -m app.main
```

The startup logs should show successful database initialization.