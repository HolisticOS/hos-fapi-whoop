"""
Supabase JWT Authentication for WHOOP API
Authenticates users directly with Supabase (same auth as Flutter app)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

from app.db.supabase_client import SupabaseClient, get_supabase

logger = structlog.get_logger(__name__)

# Security scheme for bearer token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: SupabaseClient = Depends(get_supabase)
) -> str:
    """
    Extract and verify JWT token from Authorization header
    Returns Supabase user ID (UUID)

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Supabase client instance

    Returns:
        str: Supabase user ID (UUID format)

    Raises:
        HTTPException 401: If token is invalid or expired
    """
    try:
        # Extract token from credentials
        token = credentials.credentials

        logger.info("Verifying authentication token")

        # Verify token with Supabase Auth
        # This calls Supabase's auth.get_user() which validates the JWT
        response = db.client.auth.get_user(token)

        if not response or not response.user:
            logger.warning("Invalid token - no user found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = response.user.id
        logger.info("User authenticated successfully", user_id=user_id)

        return user_id

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: SupabaseClient = Depends(get_supabase)
) -> Optional[str]:
    """
    Optional authentication - returns user_id if token is valid, None otherwise
    Useful for endpoints that work both with and without authentication

    Args:
        credentials: Optional HTTP Bearer token
        db: Supabase client instance

    Returns:
        Optional[str]: Supabase user ID (UUID) if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        response = db.client.auth.get_user(token)

        if response and response.user:
            logger.info("Optional auth succeeded", user_id=response.user.id)
            return response.user.id

        return None

    except Exception as e:
        logger.warning("Optional auth failed", error=str(e))
        return None
