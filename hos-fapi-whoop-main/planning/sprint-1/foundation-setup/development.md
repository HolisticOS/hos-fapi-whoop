# Sprint 1 - Foundation Setup: Development Plan

## Feature Description
Establish the foundational infrastructure for the hos-fapi-whoop-main microservice, including project structure, basic FastAPI application, database schema, and development environment setup. This forms the critical foundation that enables all subsequent development work.

## Technical Requirements
- **Framework**: FastAPI 0.104+ with uvicorn server
- **Database**: PostgreSQL with asyncpg driver and databases library  
- **Environment**: Python 3.9+ with proper dependency management
- **Logging**: Structured logging with structlog
- **Configuration**: Environment-based configuration with pydantic-settings
- **Containerization**: Docker support for development and deployment

## Dependencies
- **External**: PostgreSQL database instance (separate from Sahha DB)
- **Internal**: None (foundational feature)
- **Tools**: Docker, Python 3.9+, pip/poetry for dependency management
- **Accounts**: Access to database hosting service (Supabase/similar)

## Steps to Implement

### Step 1: Project Structure Setup (4 hours)
1. **Create directory structure** (1 hour)
   - Set up app/ directory with proper module organization
   - Create api/, services/, models/, config/, utils/, security/ subdirectories
   - Initialize __init__.py files for proper Python modules
   - Set up migrations/, tests/, docker/ directories

2. **Initialize basic files** (2 hours)
   - Create requirements.txt with minimal essential dependencies
   - Set up .env.example with all required environment variables
   - Create .gitignore for Python project with proper exclusions
   - Initialize basic README.md with quick start instructions

3. **Configure development environment** (1 hour)
   - Set up Docker development configuration
   - Create docker-compose.yml for local development
   - Configure development database connection
   - Verify Python virtual environment setup

### Step 2: FastAPI Application Foundation (6 hours)
1. **Core application setup** (2 hours)
   - Create app/main.py with basic FastAPI application
   - Configure CORS middleware for development
   - Set up application lifecycle events (startup/shutdown)
   - Implement basic application factory pattern

2. **Configuration management** (2 hours)
   - Create app/config/settings.py with pydantic-settings
   - Define all environment variables and their defaults
   - Implement configuration validation and error handling
   - Set up different configurations for dev/staging/production

3. **Logging infrastructure** (2 hours)
   - Configure structlog for structured logging
   - Set up log formatting and output configuration
   - Implement logging middleware for request tracking
   - Create logging utilities for consistent log messages

### Step 3: Database Infrastructure (8 hours)
1. **Database schema design** (3 hours)
   - Create migrations/init_whoop_db.sql with complete schema
   - Design whoop_users table for OAuth token storage
   - Design whoop_recovery_data, whoop_sleep_data, whoop_workout_data tables
   - Add proper indexes and constraints for performance

2. **Database models and connection** (3 hours)
   - Create app/models/database.py with SQLAlchemy table definitions
   - Implement async database connection management
   - Set up database connection pooling configuration
   - Create database initialization and cleanup functions

3. **Database testing and validation** (2 hours)
   - Test database connection and table creation
   - Validate schema design with sample data insertion
   - Implement database health check functionality
   - Create database migration execution scripts

### Step 4: Basic API Structure (6 hours)
1. **Health check endpoints** (2 hours)
   - Create app/api/health.py with basic health endpoints
   - Implement /health/ready endpoint for service readiness
   - Implement /health/live endpoint for liveness checks
   - Add database connectivity check in health endpoints

2. **API router structure** (2 hours)  
   - Create app/api/internal.py skeleton for internal endpoints
   - Create app/api/auth.py skeleton for OAuth endpoints
   - Set up proper FastAPI router configuration
   - Implement basic API key authentication dependency

3. **Basic API documentation** (2 hours)
   - Configure FastAPI automatic documentation
   - Set up proper API metadata and descriptions
   - Implement basic error response schemas
   - Test API documentation generation and accessibility

### Step 5: Development Environment Validation (4 hours)
1. **Local development setup** (2 hours)
   - Verify complete application startup
   - Test database connectivity and schema creation
   - Validate environment variable loading
   - Confirm Docker development environment functionality

2. **Basic testing framework** (2 hours)
   - Set up pytest with pytest-asyncio
   - Create tests/test_basic.py with fundamental tests
   - Implement basic application startup test
   - Create database connectivity test

## Expected Output
1. **Functional microservice foundation**:
   - FastAPI application running on localhost:8001
   - Database schema deployed and accessible
   - Health check endpoints responding correctly
   - Structured logging operational

2. **Development environment**:
   - Docker-based development setup
   - Database migrations executable
   - Environment configuration working
   - Basic test suite executable

3. **Documentation and configuration**:
   - Complete .env.example with all variables
   - README.md with setup instructions
   - Requirements.txt with pinned dependencies
   - Project structure documentation

## Acceptance Criteria
1. **Application starts successfully** using `python -m app.main`
2. **Health endpoints respond** with proper status codes and JSON responses
3. **Database schema created** without errors using migration scripts
4. **Environment variables load** correctly from .env file
5. **Docker environment runs** application and database successfully
6. **Basic tests pass** using pytest command
7. **API documentation accessible** at /docs endpoint
8. **Logging produces** structured JSON output with proper formatting

## Definition of Done
- [ ] FastAPI application starts without errors and serves requests
- [ ] Database schema successfully created with all required tables
- [ ] Health check endpoints return 200 status with valid JSON
- [ ] Environment configuration loads and validates all settings
- [ ] Docker development environment functional with database connectivity
- [ ] Basic test suite runs successfully with pytest
- [ ] API documentation generated and accessible
- [ ] Structured logging operational with proper formatting
- [ ] All dependencies installed and documented in requirements.txt
- [ ] README.md contains accurate setup and running instructions
- [ ] Code follows consistent formatting and structure standards
- [ ] Git repository properly configured with .gitignore

## Quality Gates
- **Code Review**: All code changes reviewed by senior developer
- **Testing**: All basic tests must pass before marking complete
- **Documentation**: Setup instructions verified by following README
- **Environment**: Successfully tested in clean Docker environment
- **Performance**: Application starts within 10 seconds
- **Security**: No credentials or sensitive data in code or version control