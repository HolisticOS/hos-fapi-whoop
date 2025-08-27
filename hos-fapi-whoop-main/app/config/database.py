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
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
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
    try:
        # Test connection with a simple query
        result = supabase.table("whoop_users").select("*").limit(1).execute()
        logger.info("Database connection established", table_count=len(result.data) if result.data else 0)
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False

async def close_database():
    """Close database connection"""
    # Supabase client doesn't require explicit closing
    logger.info("Database connection closed")