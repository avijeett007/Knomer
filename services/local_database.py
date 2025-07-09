"""
Local SQLite database service for testing
"""
import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID

from models.schemas import JobStatus
from config.settings import settings

logger = logging.getLogger(__name__)

class LocalDatabaseService:
    """Local SQLite database service for testing"""
    
    def __init__(self):
        self.db_path = Path(settings.SQLITE_DB_PATH)
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the database file exists"""
        if not self.db_path.exists():
            logger.warning(f"Database not found at {self.db_path}, creating new one")
            from database.sqlite_setup import setup_local_database
            setup_local_database()
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    # User Management
    def get_user(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (str(user_id),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    # API Key Management
    def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key by hash"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1", 
                    (key_hash,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}")
            return None
    
    def update_api_key_last_used(self, api_key_id: UUID) -> bool:
        """Update API key last used timestamp"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), str(api_key_id))
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating API key last used: {str(e)}")
            return False
    
    # Credit Management
    def get_user_credits(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user credit information"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_credits WHERE user_id = ?", (str(user_id),))
                row = cursor.fetchone()
                return dict(row) if row else None
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
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO credit_transactions (id, user_id, transaction_type, amount, description, job_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transaction_data.get('id', str(UUID())),
                    transaction_data['user_id'],
                    transaction_data['transaction_type'],
                    transaction_data['amount'],
                    transaction_data.get('description', ''),
                    transaction_data.get('job_id')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating credit transaction: {str(e)}")
            return None
    
    def update_user_credits_usage(self, user_id: UUID, amount: int) -> bool:
        """Update user's used credits"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_credits 
                    SET used_credits = used_credits + ?, last_updated = ?
                    WHERE user_id = ?
                """, (amount, datetime.utcnow().isoformat(), str(user_id)))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user credits usage: {str(e)}")
            return False
    
    # Job Management
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new processing job"""
        try:
            # Convert UUIDs to strings and serialize JSON fields
            if 'user_id' in job_data and isinstance(job_data['user_id'], UUID):
                job_data['user_id'] = str(job_data['user_id'])
            if 'api_key_id' in job_data and isinstance(job_data['api_key_id'], UUID):
                job_data['api_key_id'] = str(job_data['api_key_id'])
            
            # Serialize JSON fields
            input_config = json.dumps(job_data.get('input_config', {}))
            processing_options = json.dumps(job_data.get('processing_options', {}))
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO processing_jobs (
                        id, user_id, api_key_id, job_type, status, priority,
                        input_config, processing_options, estimated_credits
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_data['id'],
                    job_data['user_id'],
                    job_data['api_key_id'],
                    job_data['job_type'],
                    job_data.get('status', 'pending'),
                    job_data.get('priority', 0),
                    input_config,
                    processing_options,
                    job_data.get('estimated_credits', 0)
                ))
                conn.commit()
                return job_data['id']
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            return None
    
    def get_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM processing_jobs WHERE id = ?", (str(job_id),))
                row = cursor.fetchone()
                if row:
                    job = dict(row)
                    # Parse JSON fields
                    job['input_config'] = json.loads(job['input_config'])
                    job['processing_options'] = json.loads(job['processing_options'])
                    return job
                return None
        except Exception as e:
            logger.error(f"Error getting job: {str(e)}")
            return None
    
    def update_job_status(self, job_id: UUID, status: JobStatus, error_message: str = None) -> bool:
        """Update job status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                update_fields = ["status = ?", "updated_at = ?"]
                params = [status.value, datetime.utcnow().isoformat()]
                
                if status == JobStatus.PROCESSING:
                    update_fields.append("started_at = ?")
                    params.append(datetime.utcnow().isoformat())
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.utcnow().isoformat())
                
                if error_message:
                    update_fields.append("error_message = ?")
                    params.append(error_message)
                
                params.append(str(job_id))
                
                cursor.execute(f"""
                    UPDATE processing_jobs 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, params)
                conn.commit()
                return cursor.rowcount > 0
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE processing_jobs 
                    SET status = ?, completed_at = ?, output_file_url = ?, 
                        output_file_size = ?, output_duration = ?, 
                        actual_credits_used = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    status.value,
                    datetime.utcnow().isoformat(),
                    output_url,
                    output_size,
                    output_duration,
                    credits_used,
                    datetime.utcnow().isoformat(),
                    str(job_id)
                ))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating job completion: {str(e)}")
            return False
    
    def get_user_jobs(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's jobs with pagination"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM processing_jobs 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (str(user_id), limit, offset))
                rows = cursor.fetchall()
                jobs = []
                for row in rows:
                    job = dict(row)
                    # Parse JSON fields
                    job['input_config'] = json.loads(job['input_config'])
                    job['processing_options'] = json.loads(job['processing_options'])
                    jobs.append(job)
                return jobs
        except Exception as e:
            logger.error(f"Error getting user jobs: {str(e)}")
            return []
