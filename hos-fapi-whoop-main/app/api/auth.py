"""
WHOOP OAuth Authentication API Endpoints
Handles complete OAuth 2.0 flow with PKCE support
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
import structlog

from app.services.oauth_service import WhoopOAuthService
from app.models.schemas import (
    OAuthAuthorizationRequest, OAuthAuthorizationResponse,
    OAuthCallbackRequest, ErrorResponse
)

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize OAuth service
oauth_service = WhoopOAuthService()


@router.post("/authorize", response_model=OAuthAuthorizationResponse)
async def initiate_oauth_flow(request: OAuthAuthorizationRequest):
    """
    Initiate OAuth 2.0 authorization flow for WHOOP integration
    
    Args:
        request: OAuth authorization request with user_id and optional custom scopes
        
    Returns:
        Authorization URL and state parameter for client redirect
        
    Raises:
        HTTPException: If OAuth initiation fails
    """
    try:
        logger.info("🔐 Initiating OAuth flow", 
                   user_id=request.user_id,
                   scopes=request.scopes)
        
        auth_response = await oauth_service.initiate_oauth_flow(
            user_id=request.user_id,
            custom_scopes=request.scopes if request.scopes != ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"] else None
        )
        
        return auth_response
        
    except Exception as e:
        logger.error("❌ OAuth flow initiation failed", 
                    user_id=request.user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate OAuth flow: {str(e)}"
        )


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from WHOOP"),
    state: str = Query(..., description="State parameter for security"),
    user_id: Optional[str] = Query(None, description="Optional user ID for additional validation")
):
    """
    Handle OAuth callback from WHOOP and complete token exchange
    
    Args:
        code: Authorization code from WHOOP OAuth flow
        state: State parameter for CSRF protection
        user_id: Optional user ID for additional validation
        
    Returns:
        Connection status and user information
        
    Raises:
        HTTPException: If callback handling fails
    """
    try:
        logger.info("🔐 Processing OAuth callback", 
                   code_length=len(code) if code else 0,
                   state_length=len(state) if state else 0,
                   user_id=user_id)
        
        # Handle OAuth callback and create/update user connection
        whoop_user = await oauth_service.handle_oauth_callback(
            code=code,
            state=state,
            received_user_id=user_id
        )
        
        if not whoop_user:
            logger.error("❌ OAuth callback failed", 
                        code=code[:8] + "..." if code else None)
            raise HTTPException(
                status_code=400,
                detail="OAuth callback failed. Invalid code or state parameter."
            )
        
        logger.info("✅ OAuth callback completed successfully", 
                   user_id=whoop_user.user_id)
        
        return {
            "status": "success",
            "message": "WHOOP connection established successfully",
            "user_id": whoop_user.user_id,
            "whoop_user_id": whoop_user.whoop_user_id,
            "connected_at": whoop_user.created_at,
            "scopes": whoop_user.scopes.split() if whoop_user.scopes else [],
            "token_expires_at": whoop_user.token_expires_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ OAuth callback processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OAuth callback: {str(e)}"
        )


@router.get("/status/{user_id}")
async def get_connection_status(
    user_id: str = Path(..., description="User ID to check connection status for")
):
    """
    Get comprehensive WHOOP connection status for user
    
    Args:
        user_id: User identifier
        
    Returns:
        Detailed connection status including token validity
        
    Raises:
        HTTPException: If status check fails
    """
    try:
        logger.info("📊 Checking connection status", user_id=user_id)
        
        status = await oauth_service.get_connection_status(user_id)
        
        return status
        
    except Exception as e:
        logger.error("❌ Connection status check failed", 
                    user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check connection status: {str(e)}"
        )


@router.post("/refresh/{user_id}")
async def refresh_access_token(
    user_id: str = Path(..., description="User ID to refresh token for")
):
    """
    Manually refresh user's access token
    
    Args:
        user_id: User identifier
        
    Returns:
        Token refresh status
        
    Raises:
        HTTPException: If token refresh fails
    """
    try:
        logger.info("🔄 Manually refreshing token", user_id=user_id)
        
        success = await oauth_service.refresh_user_token(user_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to refresh access token. User may need to re-authorize."
            )
        
        # Get updated connection status
        status = await oauth_service.get_connection_status(user_id)
        
        logger.info("✅ Token refresh successful", user_id=user_id)
        
        return {
            "status": "success",
            "message": "Access token refreshed successfully",
            "user_id": user_id,
            "connection_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Token refresh failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/revoke/{user_id}")
async def revoke_connection(
    user_id: str = Path(..., description="User ID to revoke connection for")
):
    """
    Revoke WHOOP connection and invalidate tokens
    
    Args:
        user_id: User identifier
        
    Returns:
        Revocation status
        
    Raises:
        HTTPException: If revocation fails
    """
    try:
        logger.info("🔐 Revoking connection", user_id=user_id)
        
        success = await oauth_service.revoke_user_connection(user_id)
        
        if not success:
            logger.warning("⚠️ Connection revocation had issues", user_id=user_id)
            # Still return success if at least local deactivation worked
        
        logger.info("✅ Connection revocation completed", user_id=user_id)
        
        return {
            "status": "success" if success else "partial",
            "message": "WHOOP connection revoked successfully" if success 
                      else "Connection revoked locally, remote revocation may have failed",
            "user_id": user_id,
            "revoked_at": "now"
        }
        
    except Exception as e:
        logger.error("❌ Connection revocation failed", 
                    user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke connection: {str(e)}"
        )


@router.post("/validate-token/{user_id}")
async def validate_token(
    user_id: str = Path(..., description="User ID to validate token for")
):
    """
    Validate user's current access token
    
    Args:
        user_id: User identifier
        
    Returns:
        Token validation status
    """
    try:
        logger.info("🔍 Validating token", user_id=user_id)
        
        is_valid = await oauth_service.is_token_valid(user_id)
        
        return {
            "status": "valid" if is_valid else "invalid",
            "user_id": user_id,
            "token_valid": is_valid,
            "message": "Token is valid and can be used for API requests" if is_valid 
                      else "Token is expired or invalid, refresh or re-authorize required"
        }
        
    except Exception as e:
        logger.error("❌ Token validation failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate token: {str(e)}"
        )


@router.get("/oauth-config")
async def get_oauth_configuration():
    """
    Get OAuth configuration information for client integration
    
    Returns:
        OAuth configuration details (excluding sensitive information)
    """
    try:
        from app.config.settings import settings
        
        return {
            "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth",
            "token_url": "https://api.prod.whoop.com/oauth/oauth2/token",
            "client_id": settings.WHOOP_CLIENT_ID,
            "redirect_uri": settings.WHOOP_REDIRECT_URL,
            "default_scopes": [
                "offline",
                "read:profile",
                "read:cycles", 
                "read:recovery",
                "read:sleep",
                "read:workouts"
            ],
            "available_scopes": [
                "offline",
                "read:profile",
                "read:cycles",
                "read:recovery", 
                "read:sleep",
                "read:workouts"
            ],
            "pkce_supported": True,
            "pkce_required": True,
            "state_parameter_required": True,
            "min_state_length": 8
        }
        
    except Exception as e:
        logger.error("❌ Failed to get OAuth configuration", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get OAuth configuration: {str(e)}"
        )