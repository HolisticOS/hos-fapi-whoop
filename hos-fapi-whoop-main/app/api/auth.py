"""
WHOOP OAuth Authentication API Endpoints
Complete automated OAuth flow with database token storage
Integrates with Supabase JWT authentication
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from uuid import UUID
import structlog

from app.services.auth_service import WhoopAuthService
from app.core.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize auth service
auth_service = WhoopAuthService()

@router.post("/login")
async def initiate_login(current_user: str = Depends(get_current_user)):
    """
    Initiate WHOOP OAuth flow for authenticated Supabase user

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Returns:
        Authorization URL for user to complete OAuth flow
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        oauth_data = await auth_service.initiate_oauth(user_uuid)

        return {
            "success": True,
            "auth_url": oauth_data["auth_url"],
            "message": "Redirect user to auth_url to complete WHOOP OAuth flow",
            "user_id": current_user
        }

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error("Login initiation failed", user_id=current_user, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")

@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle OAuth callback from WHOOP (public endpoint)

    This endpoint receives the authorization code and exchanges it for tokens.
    Links WHOOP account to authenticated Supabase user.
    """
    try:
        result = await auth_service.handle_callback(code, state)

        # Return success page
        success_html = f"""
        <html>
            <head><title>WHOOP Authentication Success</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>🎉 WHOOP Account Linked!</h1>
                <p>Your WHOOP account has been successfully linked.</p>
                <p>WHOOP User ID: <strong>{result['whoop_user_id']}</strong></p>
                <p>You can now access your health data through the app.</p>
                <p><em>You can close this window and return to the app.</em></p>
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
                <p>There was an error linking your WHOOP account.</p>
                <p>Error: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </body>
        </html>
        """

        return HTMLResponse(content=error_html, status_code=400)

@router.get("/status")
async def get_auth_status(current_user: str = Depends(get_current_user)):
    """
    Get WHOOP authentication status for authenticated Supabase user

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Returns:
        WHOOP linkage status and token info
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        user_info = await auth_service.get_user_info(user_uuid)

        if not user_info:
            return {
                "supabase_user_id": current_user,
                "whoop_linked": False,
                "is_authenticated": False,
                "message": "WHOOP account not linked. Use POST /auth/login to link your WHOOP account."
            }

        return user_info

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error("Failed to get auth status", user_id=current_user, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get auth status: {str(e)}")

@router.post("/refresh")
async def refresh_user_token(current_user: str = Depends(get_current_user)):
    """
    Manually refresh WHOOP access token for authenticated user

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Returns:
        Token refresh status
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        # Get valid token (this will auto-refresh if needed)
        token = await auth_service.get_valid_token(user_uuid)

        if token:
            return {
                "success": True,
                "message": "WHOOP token refreshed successfully",
                "user_id": current_user
            }
        else:
            return {
                "success": False,
                "message": "Could not refresh token - user may need to re-link WHOOP account",
                "user_id": current_user
            }

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error("Token refresh failed", user_id=current_user, error=str(e))
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.get("/")
async def auth_info():
    """Get information about the authentication system"""
    return {
        "service": "WHOOP OAuth 2.0 Authentication with Supabase",
        "version": "v2-only",
        "authentication": "Supabase JWT (Bearer token required)",
        "endpoints": {
            "login": "POST /auth/login - Initiate WHOOP OAuth flow (requires Supabase auth)",
            "callback": "GET /auth/callback - OAuth callback handler (public)",
            "status": "GET /auth/status - Check WHOOP linkage status (requires Supabase auth)",
            "refresh": "POST /auth/refresh - Refresh WHOOP token (requires Supabase auth)"
        },
        "flow": [
            "1. User authenticates with Supabase directly (same as Flutter app)",
            "2. POST /auth/login with Authorization: Bearer <supabase_jwt>",
            "3. Redirect user to returned auth_url",
            "4. User completes OAuth on WHOOP",
            "5. WHOOP redirects to /auth/callback",
            "6. WHOOP account linked to Supabase user",
            "7. Use data endpoints with Supabase JWT"
        ],
        "note": "All endpoints except /callback require Authorization: Bearer <supabase_jwt_token> header"
    }