# Quick Start: Test WHOOP Connection

## ✅ What You Need

1. **WHOOP Developer Account** with API credentials
2. **Supabase/PostgreSQL** database access
3. **Python 3.11+** installed

## 🚀 3-Step Setup

### Step 1: Configure Environment

Create/edit `.env` file:

```env
# WHOOP API Credentials
WHOOP_CLIENT_ID=your_whoop_client_id_here
WHOOP_CLIENT_SECRET=your_whoop_client_secret_here
WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback

# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# Optional settings
WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v2/
ENVIRONMENT=development
```

### Step 2: Setup Database Tables

**Option A: Using Supabase Dashboard** (Recommended)

1. Go to your Supabase project dashboard
2. Click **"SQL Editor"** in the left sidebar
3. Click **"New query"**
4. Open `setup_test_db.sql` and copy all contents
5. Paste into the SQL editor
6. Click **"Run"** button

**Option B: Using psql command line**

```bash
psql -h YOUR_DB_HOST -U postgres -d postgres -f setup_test_db.sql
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## 🎯 Run the Test

```bash
python tests/test_user_daily_data.py
```

## 📝 What the Test Does

1. **Prompts for User ID**: Enter any identifier (e.g., `test_user_001`)

2. **Generates OAuth URL**: Copy and paste the URL into your browser

3. **WHOOP Login**: Log in to your WHOOP account and authorize

4. **Callback URL**: After authorization, copy the full callback URL from your browser (starts with `http://localhost:8001...`)

5. **Fetches Data**: Automatically fetches today's recovery, sleep, and workout data

6. **Saves Results**: Creates a text file in `test_output/` with all your data

## 📄 Output

Results are saved to:
```
test_output/whoop_daily_data_{user_id}_{timestamp}.txt
```

Contains:
- ✅ Recovery scores (HRV, resting heart rate)
- ✅ Sleep data (duration, stages, efficiency)
- ✅ Workout data (strain, heart rate, calories)
- ✅ Raw JSON data (for debugging)

## 🔧 Troubleshooting

### Error: "Supabase credentials not provided"

**Fix**: Make sure `SUPABASE_URL` and `SUPABASE_KEY` are set in `.env`

### Error: "relation does not exist"

**Fix**: Run the database setup SQL (`setup_test_db.sql`) in Supabase SQL Editor

### Error: "WHOOP credentials not configured"

**Fix**: Make sure `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` are in `.env`

### Error: "Invalid OAuth state"

**Fix**: Make sure you're using the callback URL from the SAME session. If it's been more than 10 minutes, restart the test.

### Error: "No data found"

**Fix**:
- Make sure your WHOOP device is synced
- Try changing the date range in the test
- Check if you have any activities recorded today

## 💾 Where Data is Stored

### Database Tables:
- `whoop_users` - Your OAuth tokens (encrypted)
- `whoop_raw_data` - Complete WHOOP API responses (JSON)
- `whoop_oauth_states` - Temporary OAuth state (auto-expires)

### Text File:
- `test_output/whoop_daily_data_*.txt` - Human-readable results

## 🔐 Security Note

- OAuth tokens are stored securely in your database
- Never commit `.env` file to version control
- The test file contains your health data - keep it private

## 📞 Need Help?

1. Check the detailed guide: `tests/RUNNING_TESTS.md`
2. Review the error messages - they usually explain what's missing
3. Make sure all 3 setup steps are completed

---

**Ready to test?** Run `python tests/test_user_daily_data.py` and follow the prompts!
