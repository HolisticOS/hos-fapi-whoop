"""
WHOOP OAuth 2.0 Authentication Service
Handles user sign-in, token storage, and automated token refresh
Integrates with Supabase authentication (UUID-based user_id)
"""

import secrets
import base64
import hashlib
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID
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
            "read:workout",  # Singular (WHOOP API v2 requirement)
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
    
    async def initiate_oauth(self, supabase_user_id: UUID) -> Dict[str, str]:
        """
        Start OAuth flow for a Supabase authenticated user
        Returns authorization URL and stores state in database

        Args:
            supabase_user_id: UUID from Supabase auth.users.id (from JWT token)
        """
        try:
            # Generate PKCE pair and state
            code_verifier, code_challenge = self.generate_pkce_pair()
            state = secrets.token_urlsafe(32)

            # Convert UUID to string for database storage
            user_id_str = str(supabase_user_id)

            # Store OAuth state in database (temporary)
            oauth_state = {
                'user_id': user_id_str,  # Supabase UUID
                'state': state,
                'code_verifier': code_verifier,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            }

            # Store in whoop_oauth_states table
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

            logger.info("OAuth flow initiated", supabase_user_id=supabase_user_id, state=state)

            return {
                'auth_url': auth_url,
                'state': state
            }

        except Exception as e:
            logger.error("Failed to initiate OAuth", supabase_user_id=supabase_user_id, error=str(e))
            raise
    
    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback, exchange code for tokens, and link WHOOP account to Supabase user

        Returns:
            Dict with supabase_user_id (UUID) and whoop_user_id
        """
        try:
            # Verify state and get stored OAuth data
            oauth_data = self.supabase.table('whoop_oauth_states').select('*').eq('state', state).execute()

            if not oauth_data.data:
                raise ValueError("Invalid or expired OAuth state")

            oauth_record = oauth_data.data[0]
            supabase_user_id = oauth_record['user_id']  # UUID string from Supabase auth
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
                # Get tokens
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )

            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")

            tokens = response.json()
            access_token = tokens['access_token']

            # Fetch WHOOP user profile to get whoop_user_id
            async with httpx.AsyncClient() as client:
                profile_response = await client.get(
                    'https://api.prod.whoop.com/developer/v1/user/profile/basic',
                    headers={'Authorization': f'Bearer {access_token}'}
                )

            if profile_response.status_code != 200:
                raise ValueError(f"Failed to fetch WHOOP profile: {profile_response.text}")

            profile = profile_response.json()
            whoop_user_id = str(profile.get('user_id'))  # WHOOP's user ID

            # Store tokens linking Supabase UUID to WHOOP user ID
            await self.store_user_tokens(supabase_user_id, whoop_user_id, tokens)

            # Clean up OAuth state
            self.supabase.table('whoop_oauth_states').delete().eq('state', state).execute()

            logger.info("OAuth callback handled successfully",
                       supabase_user_id=supabase_user_id,
                       whoop_user_id=whoop_user_id)

            return {
                'supabase_user_id': supabase_user_id,
                'whoop_user_id': whoop_user_id,
                'success': True,
                'message': 'WHOOP account linked successfully'
            }

        except Exception as e:
            logger.error("OAuth callback failed", state=state, error=str(e))
            raise
    
    async def store_user_tokens(self, supabase_user_id: str, whoop_user_id: str, tokens: Dict[str, Any]) -> None:
        """
        Store or update WHOOP tokens linked to Supabase user

        Args:
            supabase_user_id: UUID from Supabase auth.users.id (as string)
            whoop_user_id: User ID from WHOOP API
            tokens: OAuth tokens from WHOOP
        """
        try:
            access_token = tokens['access_token']
            refresh_token = tokens.get('refresh_token')
            expires_in = tokens.get('expires_in', 3600)

            # Calculate expiry time (timezone-aware)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Check if Supabase user already has a linked WHOOP account
            existing_user = self.supabase.table('whoop_users').select('*').eq('user_id', supabase_user_id).execute()

            if existing_user.data:
                # Update existing WHOOP linkage
                update_data = {
                    'whoop_user_id': whoop_user_id,  # Update in case user linked different WHOOP account
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': expires_at.isoformat(),
                    'is_active': True,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                result = self.supabase.table('whoop_users').update(update_data).eq('user_id', supabase_user_id).execute()
                logger.info("WHOOP tokens updated",
                           supabase_user_id=supabase_user_id,
                           whoop_user_id=whoop_user_id)
            else:
                # Create new WHOOP linkage for Supabase user
                user_data = {
                    'user_id': supabase_user_id,  # Supabase UUID (foreign key to auth.users.id)
                    'whoop_user_id': whoop_user_id,  # WHOOP's user ID
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': expires_at.isoformat(),
                    'is_active': True,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                result = self.supabase.table('whoop_users').insert(user_data).execute()
                logger.info("WHOOP account linked to Supabase user",
                           supabase_user_id=supabase_user_id,
                           whoop_user_id=whoop_user_id)

            logger.info("User tokens stored successfully",
                       supabase_user_id=supabase_user_id,
                       whoop_user_id=whoop_user_id)

        except Exception as e:
            logger.error("Failed to store user tokens",
                        supabase_user_id=supabase_user_id,
                        whoop_user_id=whoop_user_id,
                        error=str(e))
            raise
    
    async def get_valid_token(self, supabase_user_id: UUID) -> Optional[str]:
        """
        Get a valid WHOOP access token for Supabase user (refresh if needed)

        Args:
            supabase_user_id: UUID from Supabase auth.users.id

        Returns:
            Valid WHOOP access token or None if not linked/expired
        """
        try:
            # Convert UUID to string
            user_id_str = str(supabase_user_id)

            # Get user from database using Supabase user_id
            user_data = self.supabase.table('whoop_users').select('*').eq('user_id', user_id_str).execute()

            if not user_data.data:
                logger.warning("WHOOP account not linked", supabase_user_id=supabase_user_id)
                return None

            user = user_data.data[0]
            whoop_user_id = user['whoop_user_id']

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
                logger.info("Using cached token", supabase_user_id=supabase_user_id)
                return user['access_token']

            # Token expired, try to refresh
            if user['refresh_token']:
                logger.info("Refreshing expired token", supabase_user_id=supabase_user_id)
                new_tokens = await self.refresh_token(user['refresh_token'])

                if new_tokens:
                    await self.store_user_tokens(user_id_str, whoop_user_id, new_tokens)
                    return new_tokens['access_token']

            logger.warning("Cannot refresh token", supabase_user_id=supabase_user_id)
            return None

        except Exception as e:
            logger.error("Failed to get valid token", supabase_user_id=supabase_user_id, error=str(e))
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
    
    async def get_user_info(self, supabase_user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get WHOOP authentication status and info for Supabase user

        Args:
            supabase_user_id: UUID from Supabase auth.users.id

        Returns:
            Dict with authentication status or None if not linked
        """
        try:
            user_id_str = str(supabase_user_id)
            user_data = self.supabase.table('whoop_users').select('*').eq('user_id', user_id_str).execute()

            if not user_data.data:
                logger.info("WHOOP account not linked", supabase_user_id=supabase_user_id)
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
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                else:
                    # It's already a datetime object from Supabase
                    expires_at = expires_at_str
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)

                # Compare with timezone-aware current time
                current_time = datetime.now(timezone.utc)
                is_expired = current_time > expires_at
            else:
                is_expired = True

            return {
                'supabase_user_id': user_id_str,
                'whoop_user_id': user.get('whoop_user_id'),
                'is_authenticated': bool(user.get('access_token')) and user['is_active'],
                'token_expires_at': user['token_expires_at'],
                'is_token_expired': is_expired,
                'has_refresh_token': bool(user.get('refresh_token')),
                'created_at': user['created_at']
            }

        except Exception as e:
            logger.error("Failed to get user info", supabase_user_id=supabase_user_id, error=str(e))
            return None