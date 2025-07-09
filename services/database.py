"""
Database service for video processing API using Supabase
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import asyncpg
from supabase import create_client, Client

from config.settings import settings
from models.schemas import JobStatus, TransactionType

logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service using Supabase PostgreSQL"""
    
    def __init__(self):
        # Use local SQLite database if Supabase is not configured
        if settings.USE_SQLITE or not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            from services.local_database import LocalDatabaseService
            self.local_db = LocalDatabaseService()
            self.supabase = None
            logger.info("Using local SQLite database")
        else:
            self.supabase: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            self.local_db = None
            logger.info("Using Supabase database")
    
    # User Management
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user"""
        try:
            result = self.supabase.table('users').insert(user_data).execute()
            if result.data:
                user_id = result.data[0]['id']
                # Initialize user credits
                self._initialize_user_credits(user_id)
                return user_id
            return None
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    def get_user(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.local_db:
            return self.local_db.get_user(user_id)

        try:
            result = self.supabase.table('users').select('*').eq('id', str(user_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def _initialize_user_credits(self, user_id: str) -> bool:
        """Initialize credits for new user"""
        try:
            credit_data = {
                'user_id': user_id,
                'total_credits': settings.FREE_TIER_CREDITS,
                'used_credits': 0
            }
            result = self.supabase.table('user_credits').insert(credit_data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error initializing user credits: {str(e)}")
            return False
    
    # API Key Management
    def create_api_key(self, api_key_data: Dict[str, Any]) -> Optional[str]:
        """Create a new API key"""
        try:
            result = self.supabase.table('api_keys').insert(api_key_data).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            return None
    
    def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key by hash"""
        if self.local_db:
            return self.local_db.get_api_key_by_hash(key_hash)

        try:
            result = self.supabase.table('api_keys').select('*').eq('key_hash', key_hash).eq('is_active', True).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}")
            return None
    
    def update_api_key_last_used(self, api_key_id: UUID) -> bool:
        """Update API key last used timestamp"""
        try:
            result = self.supabase.table('api_keys').update({
                'last_used_at': datetime.utcnow().isoformat()
            }).eq('id', str(api_key_id)).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating API key last used: {str(e)}")
            return False
    
    # Credit Management
    def get_user_credits(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user credit information"""
        if self.local_db:
            return self.local_db.get_user_credits(user_id)

        try:
            result = self.supabase.table('user_credits').select('*').eq('user_id', str(user_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user credits: {str(e)}")
            return None
    
    def create_credit_transaction(self, transaction_data: Dict[str, Any]) -> Optional[str]:
        """Create a credit transaction"""
        try:
            # Convert UUID to string if needed
            if 'user_id' in transaction_data and isinstance(transaction_data['user_id'], UUID):
                transaction_data['user_id'] = str(transaction_data['user_id'])
            if 'job_id' in transaction_data and isinstance(transaction_data['job_id'], UUID):
                transaction_data['job_id'] = str(transaction_data['job_id'])
            
            result = self.supabase.table('credit_transactions').insert(transaction_data).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            logger.error(f"Error creating credit transaction: {str(e)}")
            return None
    
    def update_user_credits_usage(self, user_id: UUID, amount: int) -> bool:
        """Update user's used credits"""
        try:
            # Get current credits
            current_credits = self.get_user_credits(user_id)
            if not current_credits:
                return False
            
            new_used_credits = current_credits['used_credits'] + amount
            
            result = self.supabase.table('user_credits').update({
                'used_credits': new_used_credits,
                'last_updated': datetime.utcnow().isoformat()
            }).eq('user_id', str(user_id)).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating user credits usage: {str(e)}")
            return False
    
    def update_user_total_credits(self, user_id: UUID, amount: int) -> bool:
        """Add credits to user's total"""
        try:
            current_credits = self.get_user_credits(user_id)
            if not current_credits:
                return False
            
            new_total_credits = current_credits['total_credits'] + amount
            
            result = self.supabase.table('user_credits').update({
                'total_credits': new_total_credits,
                'last_updated': datetime.utcnow().isoformat()
            }).eq('user_id', str(user_id)).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating user total credits: {str(e)}")
            return False
    
    # Job Management
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new processing job"""
        if self.local_db:
            return self.local_db.create_job(job_data)

        try:
            # Convert UUIDs to strings
            if 'user_id' in job_data and isinstance(job_data['user_id'], UUID):
                job_data['user_id'] = str(job_data['user_id'])
            if 'api_key_id' in job_data and isinstance(job_data['api_key_id'], UUID):
                job_data['api_key_id'] = str(job_data['api_key_id'])

            result = self.supabase.table('processing_jobs').insert(job_data).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            return None
    
    def get_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        if self.local_db:
            return self.local_db.get_job(job_id)

        try:
            result = self.supabase.table('processing_jobs').select('*').eq('id', str(job_id)).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting job: {str(e)}")
            return None
    
    def update_job_status(self, job_id: UUID, status: JobStatus, error_message: str = None) -> bool:
        """Update job status"""
        if self.local_db:
            return self.local_db.update_job_status(job_id, status, error_message)

        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow().isoformat()
            }

            if status == JobStatus.PROCESSING:
                update_data['started_at'] = datetime.utcnow().isoformat()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                update_data['completed_at'] = datetime.utcnow().isoformat()

            if error_message:
                update_data['error_message'] = error_message

            result = self.supabase.table('processing_jobs').update(update_data).eq('id', str(job_id)).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            return False
    
    def update_job_completion(
        self, 
        job_id: UUID, 
        status: JobStatus, 
        output_url: str, 
        output_size: int, 
        output_duration: float, 
        credits_used: int
    ) -> bool:
        """Update job with completion details"""
        try:
            update_data = {
                'status': status.value,
                'completed_at': datetime.utcnow().isoformat(),
                'output_file_url': output_url,
                'output_file_size': output_size,
                'output_duration': output_duration,
                'actual_credits_used': credits_used,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('processing_jobs').update(update_data).eq('id', str(job_id)).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating job completion: {str(e)}")
            return False
    
    def get_user_jobs(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's jobs with pagination"""
        if self.local_db:
            return self.local_db.get_user_jobs(user_id, limit, offset)

        try:
            result = self.supabase.table('processing_jobs').select('*').eq('user_id', str(user_id)).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user jobs: {str(e)}")
            return []
    
    # Rate Limiting
    def check_rate_limit(self, api_key_id: UUID, endpoint: str, window_type: str, limit: int) -> bool:
        """Check if API key is within rate limits"""
        try:
            # This would need more complex logic for different time windows
            # For now, return True (implement proper rate limiting later)
            return True
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False
    
    # Statistics and Monitoring
    def count_total_jobs(self) -> int:
        """Count total jobs"""
        try:
            result = self.supabase.table('processing_jobs').select('id', count='exact').execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Error counting total jobs: {str(e)}")
            return 0
    
    def count_active_jobs(self) -> int:
        """Count active jobs"""
        try:
            result = self.supabase.table('processing_jobs').select('id', count='exact').in_('status', ['pending', 'processing']).execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Error counting active jobs: {str(e)}")
            return 0
