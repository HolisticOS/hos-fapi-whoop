"""
WHOOP OAuth Authentication API Endpoints
Complete automated OAuth flow with database token storage
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import structlog

from app.services.auth_service import WhoopAuthService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize auth service
auth_service = WhoopAuthService()

@router.post("/login")
async def initiate_login(user_id: str):
    """
    Initiate WHOOP OAuth flow for a user
    
    Args:
        user_id: Your internal user identifier
    
    Returns:
        Authorization URL for user to complete OAuth flow
    """
    try:
        oauth_data = await auth_service.initiate_oauth(user_id)
        
        return {
            "success": True,
            "auth_url": oauth_data["auth_url"],
            "message": "Redirect user to auth_url to complete OAuth flow",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error("Login initiation failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")

@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle OAuth callback from WHOOP
    
    This endpoint receives the authorization code and exchanges it for tokens
    """
    try:
        result = await auth_service.handle_callback(code, state)
        
        # Return success page
        success_html = f"""
        <html>
            <head><title>WHOOP Authentication Success</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>🎉 Authentication Successful!</h1>
                <p>User <strong>{result['user_id']}</strong> has been connected to WHOOP.</p>
                <p>You can now access their health data through the API.</p>
                <p><em>You can close this window.</em></p>
            </body>
        </html>
        """
        
        return HTMLResponse(content=success_html)
        
    except Exception as e:
        logger.error("OAuth callback failed", code=code[:10], state=state[:10], error=str(e))
        
        error_html = f"""
        <html>
            <head><title>WHOOP Authentication Error</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>❌ Authentication Failed</h1>
                <p>There was an error connecting to WHOOP.</p>
                <p>Error: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </body>
        </html>
        """
        
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/status/{user_id}")
async def get_auth_status(user_id: str):
    """
    Get authentication status for a user
    
    Args:
        user_id: Your internal user identifier
    
    Returns:
        User authentication status and token info
    """
    try:
        user_info = await auth_service.get_user_info(user_id)
        
        if not user_info:
            return {
                "user_id": user_id,
                "is_authenticated": False,
                "message": "User not found or not authenticated"
            }
        
        return user_info
        
    except Exception as e:
        logger.error("Failed to get auth status", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get auth status: {str(e)}")

@router.post("/refresh/{user_id}")
async def refresh_user_token(user_id: str):
    """
    Manually refresh a user's access token
    
    Args:
        user_id: Your internal user identifier
    
    Returns:
        Token refresh status
    """
    try:
        # Get valid token (this will auto-refresh if needed)
        token = await auth_service.get_valid_token(user_id)
        
        if token:
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "user_id": user_id
            }
        else:
            return {
                "success": False,
                "message": "Could not refresh token - user may need to re-authenticate",
                "user_id": user_id
            }
            
    except Exception as e:
        logger.error("Token refresh failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.get("/")
async def auth_info():
    """Get information about the authentication system"""
    return {
        "service": "WHOOP OAuth 2.0 Authentication",
        "version": "v2-only",
        "endpoints": {
            "login": "POST /auth/login - Initiate OAuth flow",
            "callback": "GET /auth/callback - OAuth callback handler", 
            "status": "GET /auth/status/{user_id} - Check auth status",
            "refresh": "POST /auth/refresh/{user_id} - Refresh token"
        },
        "flow": [
            "1. POST /auth/login with user_id",
            "2. Redirect user to returned auth_url", 
            "3. User completes OAuth on WHOOP",
            "4. WHOOP redirects to /auth/callback",
            "5. Tokens are stored automatically",
            "6. Use API endpoints with stored tokens"
        ]
    }