from supabase import create_client, Client
from app.config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# Initialize Supabase client only if valid credentials are provided
supabase: Client = None

def _initialize_supabase():
    """Initialize Supabase client with validation"""
    global supabase
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Supabase credentials not provided - running in development mode")
        return None
    
    if "your_supabase" in settings.SUPABASE_URL or "your_supabase" in settings.SUPABASE_KEY:
        logger.warning("Supabase credentials are placeholder values - running in development mode")
        return None
    
    try:
        # Use service role key if available for better RLS permissions
        api_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or settings.SUPABASE_KEY
        supabase = create_client(settings.SUPABASE_URL, api_key)
        logger.info("Supabase client initialized successfully", 
                   key_type="service_role" if hasattr(settings, 'SUPABASE_SERVICE_KEY') and settings.SUPABASE_SERVICE_KEY else "anon")
        return supabase
    except Exception as e:
        logger.error("Failed to initialize Supabase client", error=str(e))
        return None

# Initialize on module load
supabase = _initialize_supabase()

def get_supabase_client() -> Client:
    """Get configured Supabase client instance"""
    return supabase

async def init_database():
    """Initialize database connection and verify connectivity"""
    if supabase is None:
        logger.warning("Database connection skipped - running in development mode without Supabase")
        return False
    
    try:
        # Check if WHOOP tables exist (updated for Supabase auth integration)
        required_tables = [
            "whoop_users",        # OAuth tokens linked to Supabase users
            "whoop_oauth_states", # OAuth state storage
            "whoop_recovery",     # Recovery data
            "whoop_sleep",        # Sleep data
            "whoop_workout",      # Workout data
            "whoop_cycle",        # Cycle data
            "whoop_sync_log"      # Sync tracking
        ]
        missing_tables = []

        for table_name in required_tables:
            if not await table_exists(table_name):
                missing_tables.append(table_name)

        if missing_tables:
            logger.warning(
                "Database tables missing - running in degraded mode",
                missing_tables=missing_tables,
                migration_required=True,
                solution="Run SQL migration: /migrations/002_whoop_data_tables_supabase.sql"
            )
            return False

        # Test connection to whoop_users table specifically
        result = supabase.table("whoop_users").select("user_id").limit(1).execute()
        logger.info("Database connection established",
                   tables_verified=len(required_tables),
                   whoop_users_count=len(result.data) if result.data else 0)
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if "pgrst205" in error_str or "does not exist" in error_str:
            logger.warning(
                "Database tables not found - application will run in degraded mode",
                error=str(e),
                solution="Run SQL migration script: /migrations/002_whoop_data_tables_supabase.sql"
            )
            return False
        else:
            logger.error("Database connection failed", error=str(e))
            return False

async def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    if supabase is None:
        return False
        
    try:
        # Try to query the table with limit 0 (no data, just structure check)
        supabase.table(table_name).select("*").limit(0).execute()
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "pgrst205" in error_str or "does not exist" in error_str or "42p01" in error_str:
            return False
        # Re-raise unexpected errors
        raise e

async def close_database():
    """Close database connection"""
    # Supabase client doesn't require explicit closing
    logger.info("Database connection closed")