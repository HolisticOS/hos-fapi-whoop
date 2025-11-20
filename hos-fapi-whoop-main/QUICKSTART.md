# WHOOP API - Quick Start Guide

## Prerequisites
- Python 3.9+
- Virtual environment activated
- Supabase project with tables created (from migrations)
- WHOOP API credentials

## Setup

1. **Navigate to project root:**
   ```bash
   cd hos-fapi-whoop-main
   ```

2. **Activate virtual environment:**
   ```bash
   # Windows
   venv-whoop\Scripts\activate

   # Mac/Linux
   source venv-whoop/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   - Copy `.env.example` to `.env` (already done)
   - Update with your Supabase and WHOOP credentials

## Running the Server

### Option 1: Using start.py (Recommended)
```bash
python start.py
```

### Option 2: Using uvicorn directly
```bash
uvicorn app.main:app --reload --port 8009
```

### Option 3: Using Python module
```bash
python -m app.main
```

## Verify Server is Running

Once started, you should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8009
INFO:     Application startup complete.
```

Access the API documentation:
- Swagger UI: http://localhost:8009/docs
- ReDoc: http://localhost:8009/redoc

## Testing Authentication Flow

### 1. Get Supabase JWT Token
First, authenticate with your well-planned-api to get a JWT token:
```bash
POST http://localhost:8000/api/auth/login
```

### 2. Initiate WHOOP OAuth
```bash
POST http://localhost:8009/api/v1/whoop/auth/login
Authorization: Bearer <your_supabase_jwt_token>
```

### 3. Complete OAuth Flow
- Visit the returned `auth_url` in browser
- Authorize WHOOP access
- Callback will link your WHOOP account

### 4. Check Status
```bash
GET http://localhost:8009/api/v1/whoop/auth/status
Authorization: Bearer <your_supabase_jwt_token>
```

### 5. Sync Data
```bash
POST http://localhost:8009/api/v1/sync
Authorization: Bearer <your_supabase_jwt_token>
```

### 6. Fetch Data
```bash
GET http://localhost:8009/api/v1/data/recovery?days=7
Authorization: Bearer <your_supabase_jwt_token>
```

## Key Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/v1/whoop/auth/login` | POST | Yes (Supabase) | Initiate WHOOP OAuth |
| `/api/v1/whoop/auth/callback` | GET | No | OAuth callback (public) |
| `/api/v1/whoop/auth/status` | GET | Yes | Check WHOOP linkage |
| `/api/v1/sync` | POST | Yes | Sync WHOOP data to DB |
| `/api/v1/data/recovery` | GET | Yes | Get recovery data |
| `/api/v1/data/sleep` | GET | Yes | Get sleep data |
| `/api/v1/data/workouts` | GET | Yes | Get workout data |
| `/api/v1/health-metrics` | GET | Yes | Get all health data |

## Common Issues

### "No module named 'app'"
**Solution:** Make sure you're running from the project root directory, not from inside `app/`

### "SUPABASE_SERVICE_KEY not found"
**Solution:** Check your `.env` file has `SUPABASE_SERVICE_KEY` set

### "No valid access token"
**Solution:** First link your WHOOP account using `/api/v1/whoop/auth/login`

### Database errors
**Solution:** Make sure you've run the SQL migrations in the `migrations/` folder

## Architecture Overview

```
User (Flutter App)
    ↓ (Supabase JWT)
well-planned-api (Port 8000)
    ↓ (Authentication)
hos-fapi-whoop (Port 8009)
    ↓ (OAuth)
WHOOP API
    ↓ (Data stored)
Supabase Database (with RLS)
```

## Environment Variables

Key variables in `.env`:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Anonymous key (for client)
- `SUPABASE_SERVICE_KEY` - Service role key (bypasses RLS)
- `WHOOP_CLIENT_ID` - WHOOP OAuth client ID
- `WHOOP_CLIENT_SECRET` - WHOOP OAuth secret
- `WHOOP_REDIRECT_URL` - OAuth callback URL
- `API_PORT` - Server port (default: 8009)

## Development

- Server auto-reloads when using `--reload` flag
- Check logs for detailed error messages
- Use `/docs` for interactive API testing
- All endpoints require Supabase JWT except OAuth callback

## Support

For issues:
1. Check server logs
2. Verify `.env` configuration
3. Ensure database tables are created
4. Test authentication flow step-by-step
