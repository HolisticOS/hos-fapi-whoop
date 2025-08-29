# WHOOP FastAPI Microservice

A production-ready FastAPI microservice for WHOOP health data integration with OAuth 2.0 authentication and raw data storage.

## Overview

This microservice provides secure access to WHOOP health data through OAuth 2.0 authentication and stores raw JSON data for flexible processing. It's designed to integrate with larger health analytics systems and AI agents for comprehensive health insights.

## Features

- **OAuth 2.0 Integration**: Secure WHOOP API authentication with PKCE flow
- **Raw Data Storage**: Flexible JSON storage approach for all WHOOP data types
- **Real User Testing**: Tested with actual WHOOP user data (6+ months)
- **Rate Limiting**: Compliant with WHOOP API rate limits
- **Production Ready**: Proper error handling, logging, and database integration

## Quick Start

### Prerequisites

- Python 3.11+
- WHOOP Developer Account with API credentials
- Supabase or PostgreSQL database

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd hos-fapi-whoop-main
pip install -r requirements.txt
```

2. **Environment setup:**
```bash
# Create .env file with your credentials
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret  
WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback
SERVICE_API_KEY=your-secure-api-key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

3. **Database setup:**
```bash
# Apply database migrations in order
psql -f migrations/001_create_whoop_tables.sql
psql -f migrations/002_whoop_v2_migration.sql
psql -f migrations/003_cleanup_v1_tables.sql
psql -f migrations/004_oauth_tables_fixed.sql
psql -f migrations/005_whoop_raw_data_storage.sql
```

4. **Run the service:**
```bash
# Development
python -m app.main

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## API Endpoints

### Authentication
- `GET /api/v1/whoop/auth/oauth-config` - OAuth configuration
- `GET /api/v1/whoop/auth/authorize` - Start OAuth flow
- `POST /api/v1/whoop/auth/callback` - OAuth callback handler
- `GET /api/v1/whoop/auth/status/{user_id}` - Check auth status

### Data Retrieval
- `GET /api/v1/data/sleep/{user_id}` - Sleep data
- `GET /api/v1/data/recovery/{user_id}` - Recovery data  
- `GET /api/v1/data/workout/{user_id}` - Workout data
- `GET /api/v1/data/cycle/{user_id}` - Physiological cycles
- `GET /api/v1/data/profile/{user_id}` - User profile

### Raw Data Access
- `GET /api/v1/raw/{user_id}/{data_type}` - Raw JSON data
- `GET /api/v1/raw/{user_id}/summary` - Data summary

### System
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## Testing

### Automated Tests
```bash
# Core test suite
python tests/automated_test_suite.py

# Manual interactive testing
python tests/manual_testing_suite.py

# Test with real WHOOP data
python tests/test_real_user_oauth.py
```

## Documentation & Planning

This project includes comprehensive documentation for future development:
- **`/documentation`** - Architecture, API specs, and migration plans
- **`/planning`** - Sprint plans and development roadmaps  
- **`/implementation`** - Detailed implementation guides
- **`/research`** - WHOOP API v2 research and comparisons

## Project Structure

```
hos-fapi-whoop-main/
├── app/                    # FastAPI application
│   ├── api/               # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── health.py      # Health check endpoints
│   │   ├── internal.py    # Internal API endpoints
│   │   └── raw_data.py    # Raw data endpoints
│   ├── config/            # Configuration management
│   ├── models/            # Pydantic models and schemas
│   ├── services/          # Business logic services
│   │   ├── auth_service.py      # Authentication service
│   │   ├── oauth_service.py     # OAuth 2.0 handler
│   │   ├── whoop_service.py     # WHOOP API client
│   │   └── raw_data_storage.py  # Raw data management
│   └── utils/             # Utility functions
├── documentation/         # Architecture and API documentation  
├── implementation/        # Implementation guides and status
├── migrations/            # Database migration scripts
├── planning/             # Sprint plans and development roadmaps
├── research/             # WHOOP API research and analysis
└── tests/                # Test suites
    ├── automated_test_suite.py    # Automated testing
    ├── manual_testing_suite.py    # Interactive testing
    └── test_real_user_oauth.py    # Real user data testing
```

## Integration with Health Analytics

This microservice is designed to integrate with larger health analytics systems:

- **Raw Data Approach**: Stores complete WHOOP responses as JSON for flexible processing
- **AI Agent Integration**: Compatible with multi-agent health analysis systems
- **Standardized API**: RESTful endpoints for easy integration
- **Real User Data**: Tested with 6+ months of actual WHOOP user data

## Data Coverage

Successfully tested with real user data including:
- **Sleep Data**: 25+ sleep sessions with detailed metrics
- **Recovery Data**: Daily recovery scores and HRV data  
- **Workout Data**: 25+ workout sessions across different activities
- **Cycle Data**: Physiological cycle information
- **Profile Data**: User profile and device information

## Contributing

This is a production-ready microservice with comprehensive documentation for future development. See the `/planning`, `/implementation`, and `/documentation` folders for detailed development guides.

## License

[Add your license information here]