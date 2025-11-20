# Running WHOOP Tests

## Quick Start: Daily Data Test

The `test_user_daily_data.py` script is an interactive test that:
1. Connects your WHOOP account via OAuth
2. Fetches today's recovery, sleep, and workout data
3. Saves results to a text file in `test_output/`

### Prerequisites

1. **Environment Setup**
   ```bash
   # Make sure you're in the project root
   cd hos-mvp/hos-fapi-whoop/hos-fapi-whoop-main

   # Create .env file if it doesn't exist
   cp .env.example .env
   ```

2. **Configure WHOOP Credentials in .env**
   ```env
   WHOOP_CLIENT_ID=your_whoop_client_id
   WHOOP_CLIENT_SECRET=your_whoop_client_secret
   WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback

   # Database (Supabase)
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Database**
   ```bash
   # Quick setup for testing (creates all required tables)
   psql -h YOUR_DB_HOST -U YOUR_DB_USER -d YOUR_DB_NAME -f setup_test_db.sql

   # OR if using Supabase, run the SQL in the Supabase SQL Editor:
   # 1. Go to your Supabase dashboard
   # 2. Click "SQL Editor" in the left sidebar
   # 3. Create a new query
   # 4. Copy and paste contents of setup_test_db.sql
   # 5. Click "Run"

   # OR run all migrations (if you prefer the full setup)
   psql -f migrations/001_create_whoop_tables.sql
   psql -f migrations/004_oauth_tables_fixed.sql
   psql -f migrations/005_whoop_raw_data_storage.sql
   ```

### Running the Test

```bash
# Run the interactive test
python tests/test_user_daily_data.py
```

### Test Flow

1. **Enter User ID**: Provide a test user ID (e.g., `test_user_001`)

2. **OAuth Authorization**:
   - Script generates a WHOOP authorization URL
   - Copy the URL and paste in your browser
   - Log in to your WHOOP account
   - Authorize the application
   - Copy the full callback URL from browser

3. **Paste Callback URL**:
   - Return to terminal
   - Paste the full callback URL

4. **Data Fetching**:
   - Script automatically fetches recovery, sleep, and workout data
   - Progress is shown in terminal

5. **Results Saved**:
   - Results saved to `test_output/whoop_daily_data_{user_id}_{timestamp}.txt`
   - File location displayed in terminal

### Example Output

```
============================================================
  WHOOP User Login and Daily Data Test
============================================================

This script will:
  1. Connect your WHOOP account via OAuth
  2. Fetch today's recovery, sleep, and workout data
  3. Save results to a text file

------------------------------------------------------------

Enter a User ID for testing (e.g., 'test_user_001'): john_doe

[STEP 1] Starting OAuth Authorization Flow
------------------------------------------------------------

✅ Authorization URL generated successfully!

📋 Your WHOOP Authorization URL:

https://api.prod.whoop.com/oauth/oauth2/auth?client_id=...

👉 Please:
   1. Copy the URL above
   2. Paste it in your browser
   3. Log in to your WHOOP account
   4. Authorize the application
   5. You'll be redirected to a callback URL
   6. Copy the FULL callback URL from your browser

👉 Paste the full callback URL here: http://localhost:8001/...

[STEP 2] Processing OAuth Callback
------------------------------------------------------------
📝 Authorization code extracted: abc123...
🔄 Exchanging code for access token...

✅ Successfully connected to WHOOP account!

[STEP 3] Fetching Today's Health Data
------------------------------------------------------------
📅 Fetching data from: 2025-11-19 09:29:00 UTC
                  to: 2025-11-20 09:29:00 UTC

🔄 Fetching recovery data...
🔄 Fetching sleep data...
🔄 Fetching workout data...

✅ Data fetching completed!
   Recovery records: 1
   Sleep records: 1
   Workout records: 2

[STEP 4] Saving Results to File
------------------------------------------------------------

✅ Results saved successfully!
📁 File location: test_output/whoop_daily_data_john_doe_20251120_092935.txt
📊 File size: 3456 bytes

============================================================
  TEST COMPLETED SUCCESSFULLY
============================================================
✅ All steps completed!
📄 Results saved to: test_output/whoop_daily_data_john_doe_20251120_092935.txt

💡 You can now:
   - View the results file: cat test_output/whoop_daily_data_john_doe_20251120_092935.txt
   - Check test_output folder for all test results
```

### Viewing Results

```bash
# View the latest results
ls -lt test_output/
cat test_output/whoop_daily_data_*.txt

# Or open in text editor
code test_output/whoop_daily_data_*.txt
```

### Sample Results File

The generated text file includes:

```
============================================================
WHOOP DAILY DATA TEST RESULTS
============================================================
User ID: john_doe
Fetch Time: 2025-11-20 09:29:35 UTC
API Version: v2

============================================================
RECOVERY DATA
============================================================

--- Recovery Record 1 ---
Cycle ID: 12345
Recovery Score: 78%
HRV (RMSSD): 65 ms
Resting Heart Rate: 52 bpm
Recorded At: 2025-11-20T06:30:00.000Z

============================================================
SLEEP DATA
============================================================

--- Sleep Record 1 ---
Sleep ID: 550e8400-e29b-41d4-a716-446655440000
Start: 2025-11-19T22:30:00.000Z
End: 2025-11-20T06:30:00.000Z
Total Sleep Time: 7.85 hours
Time in Bed: 8.00 hours
Cycle ID: 12345

============================================================
WORKOUT DATA
============================================================

--- Workout Record 1 ---
Workout ID: 660e8400-e29b-41d4-a716-446655440001
Sport: Running (ID: 1)
Start: 2025-11-20T07:00:00.000Z
End: 2025-11-20T08:00:00.000Z
Strain Score: 14.5
Average Heart Rate: 145 bpm
Max Heart Rate: 175 bpm
Calories: 450 kcal
Distance: 8.50 km

============================================================
RAW DATA (JSON)
============================================================
[Complete JSON data for debugging...]
```

## Troubleshooting

### Error: "WHOOP credentials not configured"
- Make sure `.env` file exists with `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET`

### Error: "Database connection failed"
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Run database migrations

### Error: "Invalid callback URL"
- Make sure you copied the FULL URL from browser (including `?code=...`)
- URL should start with your REDIRECT_URL configured in .env

### Error: "No data found"
- WHOOP may not have data for today yet
- Try syncing your WHOOP device
- Check if you have any activities recorded today

### Error: "Token expired"
- Delete the user's tokens from database and reconnect
- Or use the reconnect option when prompted

## Other Test Scripts

### Automated Test Suite
```bash
python tests/automated_test_suite.py
```

### Manual Testing Suite
```bash
python tests/manual_testing_suite.py
```

### Real User OAuth Test
```bash
python tests/test_real_user_oauth.py
```
