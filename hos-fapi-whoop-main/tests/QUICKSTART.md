# Quick Start Guide - Interactive Test Script

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install requests supabase python-dotenv
   ```

2. **Configure .env file:**
   ```bash
   # Copy .env.example to .env
   cp .env.example .env

   # Edit .env and set these required values:
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_anon_key
   ```

## Running the Test

```bash
python tests/interactive_test.py
```

## What to Expect

### Step 1: Configuration Loading
The script automatically loads Supabase credentials from `.env`:
```
🔧 Loading Configuration
✓ Supabase URL: https://your-project.supabase.co...
✓ Supabase Key: eyJhb...
✓ Supabase client initialized
```

### Step 2: WHOOP API URL
Press Enter to use default (`http://localhost:8001`) or enter custom URL

### Step 3: API Connectivity Test
Verifies WHOOP API is running

### Step 4: Authentication
```
🔐 Supabase Authentication
Enter your Supabase credentials:
  Email: your-email@example.com
  Password: ********
```

The script authenticates **directly with Supabase** (same as Flutter app)

### Step 5: WHOOP Account Status
Checks if your WHOOP account is already linked

### Step 6: Link WHOOP Account (if needed)
- Opens WHOOP OAuth URL in browser
- You authorize the app
- WHOOP redirects back to complete linking

### Step 7: Data Sync (optional)
Syncs recovery, sleep, workout, and cycle data from WHOOP

### Step 8: Data Retrieval (optional)
Fetches and displays synced data

## Troubleshooting

### "Missing Supabase configuration in .env file"
- Make sure `.env` exists in project root
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are set

### "WHOOP API is NOT reachable"
- Start the WHOOP API server: `python start.py`
- Verify it's running on port 8001

### "Authentication failed: Invalid login credentials"
- Check your email/password are correct
- Verify you have an account in Supabase

### "WHOOP not linked"
- Follow the OAuth flow when prompted
- Make sure you complete authorization on WHOOP's website

## Environment Variables Reference

### Required for Testing:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase anonymous/public key

### Required for Server:
- `SUPABASE_SERVICE_KEY` - Supabase service role key (server-side only)
- `WHOOP_CLIENT_ID` - Your WHOOP OAuth client ID
- `WHOOP_CLIENT_SECRET` - Your WHOOP OAuth client secret
- `WHOOP_REDIRECT_URL` - OAuth callback URL (default: http://localhost:8001/api/v1/whoop/auth/callback)

## Next Steps

After successful testing:
1. Review synced data in Supabase dashboard
2. Test data retrieval endpoints
3. Integrate with Flutter app
4. Set up automated data sync schedule
