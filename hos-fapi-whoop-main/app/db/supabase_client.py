"""
Supabase client for WHOOP API
Connects directly to Supabase for authentication and data storage
"""
import os
from supabase import create_client, Client
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class SupabaseClient:
    """Supabase client wrapper"""

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set"
            )

        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase client initialized", url=self.url)

    def get_client(self) -> Client:
        """Get Supabase client instance"""
        return self.client


# Global instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """
    Dependency injection for Supabase client
    Creates singleton instance on first call

    Usage:
        @app.get("/endpoint")
        async def my_endpoint(db: SupabaseClient = Depends(get_supabase)):
            # Use db.client to query Supabase
            pass
    """
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = SupabaseClient()

    return _supabase_client


def reset_supabase_client():
    """Reset client (useful for testing)"""
    global _supabase_client
    _supabase_client = None
