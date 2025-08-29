"""
WHOOP OAuth 2.0 Authentication Service
Handles user sign-in, token storage, and automated token refresh
"""

import secrets
import base64
import hashlib
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
import structlog

from app.config.settings import settings
from app.config.database import get_supabase_client

logger = structlog.get_logger(__name__)

class WhoopAuthService:
    """Complete OAuth service with database token storage"""
    
    def __init__(self):
        self.client_id = settings.WHOOP_CLIENT_ID
        self.client_secret = settings.WHOOP_CLIENT_SECRET
        self.redirect_uri = settings.WHOOP_REDIRECT_URL
        self.supabase = get_supabase_client()
        
        # WHOOP OAuth URLs
        self.auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
        self.token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
        
        # Complete scopes for all WHOOP data access
        self.scopes = [
            "read:profile",
            "read:recovery", 
            "read:sleep",
            "read:workouts",  # Note: plural form
            "read:cycles",
            "offline"
        ]
    
    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    async def initiate_oauth(self, user_id: str) -> Dict[str, str]:
        """
        Start OAuth flow for a user
        Returns authorization URL and stores state in database
        """
        try:
            # Generate PKCE pair and state
            code_verifier, code_challenge = self.generate_pkce_pair()
            state = secrets.token_urlsafe(32)
            
            # Store OAuth state in database (temporary)
            oauth_state = {
                'user_id': user_id,
                'state': state,
                'code_verifier': code_verifier,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            }
            
            # Store in whoop_oauth_states table (we'll create this)
            result = self.supabase.table('whoop_oauth_states').insert(oauth_state).execute()
            
            # Build authorization URL
            auth_params = {
                'client_id': self.client_id,
                'response_type': 'code',
                'scope': ' '.join(self.scopes),
                'redirect_uri': self.redirect_uri,
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            import urllib.parse
            auth_url = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"
            
            logger.info("OAuth flow initiated", user_id=user_id, state=state)
            
            return {
                'auth_url': auth_url,
                'state': state
            }
            
        except Exception as e:
            logger.error("Failed to initiate OAuth", user_id=user_id, error=str(e))
            raise
    
    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for tokens
        """
        try:
            # Verify state and get stored OAuth data
            oauth_data = self.supabase.table('whoop_oauth_states').select('*').eq('state', state).execute()
            
            if not oauth_data.data:
                raise ValueError("Invalid or expired OAuth state")
            
            oauth_record = oauth_data.data[0]
            user_id = oauth_record['user_id']
            code_verifier = oauth_record['code_verifier']
            
            # Exchange authorization code for tokens
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.redirect_uri,
                'code_verifier': code_verifier
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
            
            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")
            
            tokens = response.json()
            
            # Store tokens in database
            await self.store_user_tokens(user_id, tokens)
            
            # Clean up OAuth state
            self.supabase.table('whoop_oauth_states').delete().eq('state', state).execute()
            
            logger.info("OAuth callback handled successfully", user_id=user_id)
            
            return {
                'user_id': user_id,
                'success': True,
                'message': 'Authentication successful'
            }
            
        except Exception as e:
            logger.error("OAuth callback failed", state=state, error=str(e))
            raise
    
    async def store_user_tokens(self, user_id: str, tokens: Dict[str, Any]) -> None:
        """Store or update user tokens in database"""
        try:
            access_token = tokens['access_token']
            refresh_token = tokens.get('refresh_token')
            expires_in = tokens.get('expires_in', 3600)
            
            # Calculate expiry time (timezone-aware)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            # Check if user already exists
            existing_user = self.supabase.table('whoop_users').select('*').eq('whoop_user_id', user_id).execute()
            
            if existing_user.data:
                # Update existing user
                update_data = {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': expires_at.isoformat(),
                    'is_active': True,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = self.supabase.table('whoop_users').update(update_data).eq('whoop_user_id', user_id).execute()
                logger.info("User tokens updated", user_id=user_id)
            else:
                # Create new user - generate a UUID for user_id
                import uuid
                
                user_data = {
                    'user_id': str(uuid.uuid4()),  # Generate UUID for the user_id column
                    'whoop_user_id': user_id,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': expires_at.isoformat(),
                    'is_active': True,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = self.supabase.table('whoop_users').insert(user_data).execute()
                logger.info("New user created", user_id=user_id)
            
            logger.info("User tokens stored", user_id=user_id)
            
        except Exception as e:
            logger.error("Failed to store user tokens", user_id=user_id, error=str(e))
            raise
    
    async def get_valid_token(self, user_id: str) -> Optional[str]:
        """Get a valid access token for user (refresh if needed)"""
        try:
            # Get user from database
            user_data = self.supabase.table('whoop_users').select('*').eq('whoop_user_id', user_id).execute()
            
            if not user_data.data:
                logger.warning("User not found", user_id=user_id)
                return None
            
            user = user_data.data[0]
            
            # Check if token is still valid
            expires_at_str = user['token_expires_at']
            if isinstance(expires_at_str, str):
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str.replace('Z', '+00:00')
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = expires_at_str
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) < expires_at - timedelta(minutes=5):  # 5-minute buffer
                return user['access_token']
            
            # Token expired, try to refresh
            if user['refresh_token']:
                logger.info("Refreshing expired token", user_id=user_id)
                new_tokens = await self.refresh_token(user['refresh_token'])
                
                if new_tokens:
                    await self.store_user_tokens(user_id, new_tokens)
                    return new_tokens['access_token']
            
            logger.warning("Cannot refresh token", user_id=user_id)
            return None
            
        except Exception as e:
            logger.error("Failed to get valid token", user_id=user_id, error=str(e))
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an expired access token"""
        try:
            token_data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Token refresh failed", status=response.status_code, response=response.text)
                return None
                
        except Exception as e:
            logger.error("Token refresh error", error=str(e))
            return None
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user authentication status and info"""
        try:
            user_data = self.supabase.table('whoop_users').select('*').eq('whoop_user_id', user_id).execute()
            
            if not user_data.data:
                return None
            
            user = user_data.data[0]
            
            # Handle timezone-aware datetime comparison
            if user.get('token_expires_at'):
                expires_at_str = user['token_expires_at']
                # Handle both ISO formats with and without timezone info
                if isinstance(expires_at_str, str):
                    if expires_at_str.endswith('Z'):
                        expires_at_str = expires_at_str.replace('Z', '+00:00')
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=datetime.now().astimezone().tzinfo)
                else:
                    # It's already a datetime object from Supabase
                    expires_at = expires_at_str
                
                # Compare with timezone-aware current time
                current_time = datetime.now(timezone.utc)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                is_expired = current_time > expires_at
            else:
                is_expired = True
            
            return {
                'user_id': user_id,
                'is_authenticated': bool(user.get('access_token')) and user['is_active'],
                'token_expires_at': user['token_expires_at'],
                'is_token_expired': is_expired,
                'has_refresh_token': bool(user.get('refresh_token')),
                'created_at': user['created_at']
            }
            
        except Exception as e:
            logger.error("Failed to get user info", user_id=user_id, error=str(e))
            return None