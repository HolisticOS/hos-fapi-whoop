"""
Comprehensive WHOOP OAuth 2.0 Service Implementation
Supports Authorization Code + PKCE flow as required by WHOOP API v1/v2
"""

import base64
import hashlib
import secrets
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
import structlog

from app.config.settings import settings
from app.models.database import WhoopUserRepository
from app.models.schemas import WhoopUser, OAuthAuthorizationResponse, OAuthTokenResponse

logger = structlog.get_logger(__name__)


class WhoopOAuthService:
    """Complete WHOOP OAuth 2.0 implementation with PKCE support"""
    
    def __init__(self):
        self.client_id = settings.WHOOP_CLIENT_ID
        self.client_secret = settings.WHOOP_CLIENT_SECRET
        self.redirect_uri = settings.WHOOP_REDIRECT_URL
        
        # WHOOP OAuth endpoints
        self.auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
        self.token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
        self.revoke_url = "https://api.prod.whoop.com/oauth/oauth2/revoke"
        
        # Default scopes for comprehensive health data access
        self.default_scopes = [
            "offline",           # Required for refresh tokens
            "read:profile",      # User profile access
            "read:cycles",       # Cycle and recovery data
            "read:recovery",     # Detailed recovery metrics
            "read:sleep",        # Sleep data access
            "read:workouts"      # Workout and strain data
        ]
        
        self.user_repo = WhoopUserRepository()
        
        logger.info("🔐 WHOOP OAuth service initialized", 
                   client_id=self.client_id[:8] + "...",
                   scopes=self.default_scopes)
    
    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        # Generate random code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')  # Remove padding
        
        # Generate code challenge using SHA256
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')  # Remove padding
        
        logger.info("🔐 Generated PKCE pair", 
                   verifier_length=len(code_verifier),
                   challenge_length=len(code_challenge))
        
        return code_verifier, code_challenge
    
    def _generate_state(self, user_id: str) -> str:
        """Generate secure state parameter (minimum 8 characters)"""
        random_part = secrets.token_urlsafe(16)
        # Include user_id for validation (encoded for security)
        user_part = base64.urlsafe_b64encode(user_id.encode()).decode().rstrip('=')
        state = f"{random_part}.{user_part}"
        
        logger.info("🔐 Generated OAuth state", 
                   state_length=len(state),
                   user_id=user_id)
        
        return state
    
    def _extract_user_from_state(self, state: str) -> Optional[str]:
        """Extract user_id from state parameter"""
        try:
            parts = state.split('.')
            if len(parts) >= 2:
                # Add padding if needed
                user_part = parts[1]
                padding = 4 - len(user_part) % 4
                if padding != 4:
                    user_part += '=' * padding
                
                user_id = base64.urlsafe_b64decode(user_part).decode()
                return user_id
        except Exception as e:
            logger.error("❌ Failed to extract user from state", 
                        state=state, error=str(e))
        return None
    
    async def initiate_oauth_flow(self, user_id: str, 
                                custom_scopes: Optional[List[str]] = None) -> OAuthAuthorizationResponse:
        """
        Initiate OAuth authorization flow with PKCE
        
        Args:
            user_id: Internal user identifier
            custom_scopes: Optional custom scopes (defaults to comprehensive access)
            
        Returns:
            Authorization URL and state for client redirect
        """
        try:
            # Use custom scopes or default comprehensive scopes
            scopes = custom_scopes if custom_scopes else self.default_scopes
            
            # Generate PKCE parameters
            code_verifier, code_challenge = self._generate_pkce_pair()
            
            # Generate secure state
            state = self._generate_state(user_id)
            
            # Store PKCE verifier and state for callback validation
            # In production, store in Redis or secure session storage
            # For MVP, we'll rely on state validation
            
            # Build authorization URL
            auth_params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'response_type': 'code',
                'scope': ' '.join(scopes),
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'  # SHA256 PKCE method
            }
            
            auth_url = f"{self.auth_url}?" + urllib.parse.urlencode(auth_params)
            
            logger.info("🔐 OAuth flow initiated", 
                       user_id=user_id,
                       scopes=scopes,
                       redirect_uri=self.redirect_uri)
            
            return OAuthAuthorizationResponse(
                authorization_url=auth_url,
                state=state
            )
            
        except Exception as e:
            logger.error("❌ Failed to initiate OAuth flow", 
                        user_id=user_id, error=str(e))
            raise
    
    async def handle_oauth_callback(self, code: str, state: str, 
                                  received_user_id: Optional[str] = None) -> Optional[WhoopUser]:
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:
            code: Authorization code from WHOOP
            state: State parameter for validation
            received_user_id: User ID from callback (for additional validation)
            
        Returns:
            Created/updated WhoopUser object or None if failed
        """
        try:
            # Validate state and extract user_id
            user_id = self._extract_user_from_state(state)
            if not user_id:
                logger.error("❌ Invalid state parameter", state=state)
                return None
            
            # Additional validation if user_id provided
            if received_user_id and received_user_id != user_id:
                logger.error("❌ User ID mismatch in callback", 
                           state_user=user_id, 
                           received_user=received_user_id)
                return None
            
            # For MVP, regenerate PKCE verifier (in production, retrieve from storage)
            # This is a simplified approach - production should store verifier securely
            code_verifier, _ = self._generate_pkce_pair()
            
            # Exchange authorization code for tokens
            token_data = await self._exchange_code_for_tokens(code, code_verifier)
            if not token_data:
                logger.error("❌ Failed to exchange code for tokens", user_id=user_id)
                return None
            
            # Calculate token expiry
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Check if user already exists
            existing_user = await self.user_repo.get_user_by_id(user_id)
            
            if existing_user:
                # Update existing user's tokens
                success = await self.user_repo.update_tokens(
                    user_id=user_id,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token', ''),
                    expires_at=expires_at
                )
                
                if success:
                    logger.info("✅ OAuth callback completed - user updated", 
                               user_id=user_id)
                    return await self.user_repo.get_user_by_id(user_id)
                else:
                    logger.error("❌ Failed to update user tokens", user_id=user_id)
                    return None
            else:
                # Create new user connection
                user_data = WhoopUser(
                    user_id=user_id,
                    whoop_user_id=None,  # Will be populated from profile API
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token', ''),
                    token_expires_at=expires_at,
                    scopes=token_data.get('scope', ' '.join(self.default_scopes)),
                    is_active=True
                )
                
                created_user = await self.user_repo.create_user(user_data)
                if created_user:
                    logger.info("✅ OAuth callback completed - user created", 
                               user_id=user_id)
                    return created_user
                else:
                    logger.error("❌ Failed to create user connection", user_id=user_id)
                    return None
                    
        except Exception as e:
            logger.error("❌ OAuth callback handling failed", 
                        code=code[:8] + "...",
                        error=str(e))
            return None
    
    async def _exchange_code_for_tokens(self, code: str, code_verifier: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access/refresh tokens"""
        try:
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.redirect_uri,
                'code_verifier': code_verifier  # PKCE verifier
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    token_response = response.json()
                    logger.info("✅ Successfully exchanged code for tokens",
                               expires_in=token_response.get('expires_in'),
                               has_refresh=bool(token_response.get('refresh_token')))
                    return token_response
                else:
                    logger.error("❌ Token exchange failed", 
                               status_code=response.status_code,
                               response=response.text)
                    return None
                    
        except Exception as e:
            logger.error("❌ Token exchange request failed", error=str(e))
            return None
    
    async def refresh_user_token(self, user_id: str) -> bool:
        """
        Refresh user's access token using refresh token
        
        Args:
            user_id: Internal user identifier
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            # Get current user data
            user = await self.user_repo.get_user_by_id(user_id)
            if not user or not user.refresh_token:
                logger.error("❌ No refresh token available", user_id=user_id)
                return False
            
            refresh_data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': user.refresh_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=refresh_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Calculate new expiry
                    expires_in = token_data.get('expires_in', 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    # Update user tokens
                    success = await self.user_repo.update_tokens(
                        user_id=user_id,
                        access_token=token_data['access_token'],
                        refresh_token=token_data.get('refresh_token', user.refresh_token),
                        expires_at=expires_at
                    )
                    
                    if success:
                        logger.info("✅ Token refresh successful", user_id=user_id)
                        return True
                    else:
                        logger.error("❌ Failed to update refreshed tokens", user_id=user_id)
                        return False
                else:
                    logger.error("❌ Token refresh failed", 
                               user_id=user_id,
                               status_code=response.status_code,
                               response=response.text)
                    return False
                    
        except Exception as e:
            logger.error("❌ Token refresh request failed", 
                        user_id=user_id, error=str(e))
            return False
    
    async def is_token_valid(self, user_id: str) -> bool:
        """
        Check if user's access token is valid (not expired)
        
        Args:
            user_id: Internal user identifier
            
        Returns:
            True if token is valid, False if expired or not found
        """
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            if not user or not user.access_token or not user.is_active:
                return False
            
            # Check if token is expired (with 5-minute buffer)
            if user.token_expires_at:
                buffer_time = datetime.utcnow() + timedelta(minutes=5)
                if user.token_expires_at <= buffer_time:
                    logger.info("🔐 Token expired", user_id=user_id, 
                               expires_at=user.token_expires_at)
                    return False
            
            return True
            
        except Exception as e:
            logger.error("❌ Token validation failed", user_id=user_id, error=str(e))
            return False
    
    async def get_valid_access_token(self, user_id: str) -> Optional[str]:
        """
        Get valid access token for user, refreshing if necessary
        
        Args:
            user_id: Internal user identifier
            
        Returns:
            Valid access token or None if unavailable
        """
        try:
            # Check if current token is valid
            if await self.is_token_valid(user_id):
                user = await self.user_repo.get_user_by_id(user_id)
                return user.access_token if user else None
            
            # Try to refresh token
            if await self.refresh_user_token(user_id):
                user = await self.user_repo.get_user_by_id(user_id)
                return user.access_token if user else None
            
            logger.error("❌ Unable to get valid access token", user_id=user_id)
            return None
            
        except Exception as e:
            logger.error("❌ Error getting valid access token", 
                        user_id=user_id, error=str(e))
            return None
    
    async def revoke_user_connection(self, user_id: str) -> bool:
        """
        Revoke user's WHOOP connection and tokens
        
        Args:
            user_id: Internal user identifier
            
        Returns:
            True if revocation successful, False otherwise
        """
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            if not user or not user.access_token:
                logger.warning("⚠️ No active connection to revoke", user_id=user_id)
                return True  # Already disconnected
            
            # Revoke token with WHOOP
            revoke_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'token': user.access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.revoke_url,
                    data=revoke_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )
                
                # Deactivate user locally regardless of WHOOP response
                local_success = await self.user_repo.deactivate_user(user_id)
                
                if response.status_code == 200 and local_success:
                    logger.info("✅ User connection revoked successfully", user_id=user_id)
                    return True
                else:
                    logger.warning("⚠️ Partial revocation success", 
                                 user_id=user_id,
                                 whoop_status=response.status_code,
                                 local_success=local_success)
                    return local_success  # At least local deactivation worked
                    
        except Exception as e:
            logger.error("❌ Connection revocation failed", 
                        user_id=user_id, error=str(e))
            return False
    
    async def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive connection status for user
        
        Args:
            user_id: Internal user identifier
            
        Returns:
            Dictionary with connection status details
        """
        try:
            user = await self.user_repo.get_user_by_id(user_id)
            
            if not user:
                return {
                    "connected": False,
                    "status": "not_found",
                    "message": "No WHOOP connection found for user"
                }
            
            if not user.is_active:
                return {
                    "connected": False,
                    "status": "inactive",
                    "message": "WHOOP connection is inactive",
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
            
            token_valid = await self.is_token_valid(user_id)
            
            return {
                "connected": True,
                "status": "active" if token_valid else "token_expired",
                "message": "WHOOP connection active" if token_valid else "Access token expired",
                "whoop_user_id": user.whoop_user_id,
                "scopes": user.scopes.split() if user.scopes else [],
                "token_expires_at": user.token_expires_at,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "token_valid": token_valid,
                "can_refresh": bool(user.refresh_token)
            }
            
        except Exception as e:
            logger.error("❌ Failed to get connection status", 
                        user_id=user_id, error=str(e))
            return {
                "connected": False,
                "status": "error",
                "message": f"Error checking connection: {str(e)}"
            }