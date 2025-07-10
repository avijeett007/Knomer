"""
Authentication service for API key management
"""
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

from passlib.context import CryptContext
# Import database service based on configuration
from config.settings import settings
if settings.USE_SQLITE:
    from services.database_sqlite import SQLiteDatabaseService as DatabaseService
else:
    from services.database import DatabaseService
from config.settings import settings

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication and API key management service"""
    
    def __init__(self, db_service=None):
        self.db_service = db_service if db_service else DatabaseService()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def generate_api_key(self) -> tuple[str, str, str]:
        """
        Generate a new API key
        
        Returns:
            Tuple of (api_key, key_hash, key_prefix)
        """
        # Generate random key
        random_part = secrets.token_urlsafe(32)
        api_key = f"{settings.API_KEY_PREFIX}{random_part}"
        
        # Create hash for storage
        key_hash = self._hash_api_key(api_key)
        
        # Create prefix for identification
        key_prefix = api_key[:10]
        
        return api_key, key_hash, key_prefix
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_api_key(
        self, 
        user_id: UUID, 
        name: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        rate_limits: Optional[Dict[str, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new API key for user
        
        Args:
            user_id: User ID
            name: Optional name for the key
            expires_at: Optional expiration date
            rate_limits: Optional rate limit overrides
            
        Returns:
            Dict with API key info including the secret key (only returned once)
        """
        try:
            # Generate API key
            api_key, key_hash, key_prefix = self.generate_api_key()
            
            # Prepare API key data
            api_key_data = {
                'user_id': str(user_id),
                'key_hash': key_hash,
                'key_prefix': key_prefix,
                'name': name,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'rate_limit_per_minute': rate_limits.get('per_minute', settings.DEFAULT_RATE_LIMIT_PER_MINUTE) if rate_limits else settings.DEFAULT_RATE_LIMIT_PER_MINUTE,
                'rate_limit_per_hour': rate_limits.get('per_hour', settings.DEFAULT_RATE_LIMIT_PER_HOUR) if rate_limits else settings.DEFAULT_RATE_LIMIT_PER_HOUR,
                'rate_limit_per_day': rate_limits.get('per_day', settings.DEFAULT_RATE_LIMIT_PER_DAY) if rate_limits else settings.DEFAULT_RATE_LIMIT_PER_DAY,
                'is_active': True
            }
            
            # Save to database
            api_key_id = self.db_service.create_api_key(api_key_data)
            
            if api_key_id:
                return {
                    'id': api_key_id,
                    'api_key': api_key,  # Only returned once
                    'key_prefix': key_prefix,
                    'name': name,
                    'expires_at': expires_at,
                    'rate_limit_per_minute': api_key_data['rate_limit_per_minute'],
                    'rate_limit_per_hour': api_key_data['rate_limit_per_hour'],
                    'rate_limit_per_day': api_key_data['rate_limit_per_day'],
                    'created_at': datetime.utcnow()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            return None
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return user info
        
        Args:
            api_key: API key to validate
            
        Returns:
            User and API key info if valid, None otherwise
        """
        try:
            # Hash the provided key
            key_hash = self._hash_api_key(api_key)
            
            # Get API key from database
            api_key_info = self.db_service.get_api_key_by_hash(key_hash)
            
            if not api_key_info:
                logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
                return None
            
            # Check if key is active
            if not api_key_info.get('is_active', False):
                logger.warning(f"Inactive API key used: {api_key_info.get('key_prefix')}")
                return None
            
            # Check expiration
            expires_at = api_key_info.get('expires_at')
            if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
                logger.warning(f"Expired API key used: {api_key_info.get('key_prefix')}")
                return None
            
            # Get user info
            user_id = UUID(api_key_info['user_id'])
            user_info = self.db_service.get_user(user_id)
            
            if not user_info or not user_info.get('is_active', False):
                logger.warning(f"API key for inactive user: {user_id}")
                return None
            
            # Update last used timestamp
            self.db_service.update_api_key_last_used(UUID(api_key_info['id']))
            
            # Check rate limits
            if not await self._check_rate_limits(UUID(api_key_info['id']), api_key_info):
                logger.warning(f"Rate limit exceeded for API key: {api_key_info.get('key_prefix')}")
                return None
            
            return {
                'user_id': str(user_id),
                'api_key_id': api_key_info['id'],
                'user_email': user_info['email'],
                'user_name': user_info.get('name'),
                'subscription_tier': user_info.get('subscription_tier', 'free'),
                'rate_limits': {
                    'per_minute': api_key_info.get('rate_limit_per_minute'),
                    'per_hour': api_key_info.get('rate_limit_per_hour'),
                    'per_day': api_key_info.get('rate_limit_per_day')
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None
    
    async def _check_rate_limits(self, api_key_id: UUID, api_key_info: Dict[str, Any]) -> bool:
        """
        Check if API key is within rate limits
        
        Args:
            api_key_id: API key ID
            api_key_info: API key information
            
        Returns:
            True if within limits, False otherwise
        """
        try:
            # Check different time windows
            limits = [
                ('minute', api_key_info.get('rate_limit_per_minute', 10)),
                ('hour', api_key_info.get('rate_limit_per_hour', 100)),
                ('day', api_key_info.get('rate_limit_per_day', 1000))
            ]
            
            for window_type, limit in limits:
                if not self.db_service.check_rate_limit(api_key_id, 'api_call', window_type, limit):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            return False
    
    async def revoke_api_key(self, api_key_id: UUID, user_id: UUID) -> bool:
        """
        Revoke (deactivate) an API key
        
        Args:
            api_key_id: API key ID to revoke
            user_id: User ID (for authorization)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify the API key belongs to the user
            api_key_info = self.db_service.get_api_key(api_key_id)
            if not api_key_info or api_key_info['user_id'] != str(user_id):
                return False
            
            # Deactivate the key
            return self.db_service.deactivate_api_key(api_key_id)
            
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False
    
    async def list_user_api_keys(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        List all API keys for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of API key info (without secrets)
        """
        try:
            return self.db_service.get_user_api_keys(user_id)
        except Exception as e:
            logger.error(f"Error listing API keys: {str(e)}")
            return []
    
    def create_user(self, email: str, name: Optional[str] = None) -> Optional[str]:
        """
        Create a new user
        
        Args:
            email: User email
            name: Optional user name
            
        Returns:
            User ID if successful, None otherwise
        """
        try:
            user_data = {
                'email': email,
                'name': name,
                'subscription_tier': 'free',
                'is_active': True
            }
            
            return self.db_service.create_user(user_data)
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None
