"""
SQLite database service for local testing
"""
import sqlite3
import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from pathlib import Path

from models.schemas import JobStatus, TransactionType

logger = logging.getLogger(__name__)

class SQLiteDatabaseService:
    """SQLite database service for local testing"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "database" / "test_database.db"
        self.db_path = str(db_path)
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure database exists and is accessible"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.close()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False
    
    # User Management
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            user_id = user_data.get('id', str(uuid.uuid4()))
            cursor.execute("""
                INSERT INTO users (id, email, name, subscription_tier, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                user_data['email'],
                user_data.get('name'),
                user_data.get('subscription_tier', 'free'),
                user_data.get('is_active', True)
            ))
            
            conn.commit()
            conn.close()
            
            # Initialize user credits
            self._initialize_user_credits(user_id)
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE id = ?", (str(user_id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def _initialize_user_credits(self, user_id: str) -> bool:
        """Initialize credits for new user"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_credits (id, user_id, total_credits, used_credits)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), user_id, 100, 0))  # 100 free credits
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user credits: {e}")
            return False
    
    # API Key Management
    def create_api_key(self, api_key_data: Dict[str, Any]) -> Optional[str]:
        """Create a new API key"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            api_key_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, is_active, 
                                    rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api_key_id,
                api_key_data['user_id'],
                api_key_data['key_hash'],
                api_key_data['key_prefix'],
                api_key_data.get('name'),
                api_key_data.get('is_active', True),
                api_key_data.get('rate_limit_per_minute', 10),
                api_key_data.get('rate_limit_per_hour', 100),
                api_key_data.get('rate_limit_per_day', 1000)
            ))
            
            conn.commit()
            conn.close()
            return api_key_id
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return None
    
    def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key by hash"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1
            """, (key_hash,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting API key: {e}")
            return None
    
    def update_api_key_last_used(self, api_key_id: UUID) -> bool:
        """Update API key last used timestamp"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE api_keys SET last_used_at = ? WHERE id = ?
            """, (datetime.utcnow().isoformat(), str(api_key_id)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating API key last used: {e}")
            return False
    
    # Credit Management
    def get_user_credits(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user credit information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT *, (total_credits - used_credits) as remaining_credits 
                FROM user_credits WHERE user_id = ?
            """, (str(user_id),))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user credits: {e}")
            return None
    
    def create_credit_transaction(self, transaction_data: Dict[str, Any]) -> Optional[str]:
        """Create a credit transaction"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            transaction_id = str(uuid.uuid4())

            # Convert UUIDs to strings for SQLite compatibility
            user_id = str(transaction_data['user_id']) if transaction_data['user_id'] else None
            job_id = str(transaction_data.get('job_id')) if transaction_data.get('job_id') else None

            cursor.execute("""
                INSERT INTO credit_transactions (id, user_id, transaction_type, amount, description, job_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transaction_id,
                user_id,
                transaction_data['transaction_type'],
                transaction_data['amount'],
                transaction_data.get('description'),
                job_id
            ))
            
            conn.commit()
            conn.close()
            return transaction_id
            
        except Exception as e:
            logger.error(f"Error creating credit transaction: {e}")
            return None

    def update_credit_transaction_description(self, job_id: UUID, description: str) -> bool:
        """Update credit transaction description"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE credit_transactions
                SET description = ?
                WHERE job_id = ?
            """, (description, str(job_id)))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating credit transaction description: {e}")
            return False

    def get_user_credit_transactions(self, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's credit transaction history"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM credit_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (str(user_id), limit))

            rows = cursor.fetchall()
            conn.close()

            transactions = []
            for row in rows:
                transactions.append(dict(row))

            return transactions

        except Exception as e:
            logger.error(f"Error getting user credit transactions: {e}")
            return []

    def update_user_credits_usage(self, user_id: UUID, amount: int) -> bool:
        """Update user's used credits"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_credits 
                SET used_credits = used_credits + ?, last_updated = ?
                WHERE user_id = ?
            """, (amount, datetime.utcnow().isoformat(), str(user_id)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user credits usage: {e}")
            return False
    
    def update_user_total_credits(self, user_id: UUID, amount: int) -> bool:
        """Add credits to user's total"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_credits 
                SET total_credits = total_credits + ?, last_updated = ?
                WHERE user_id = ?
            """, (amount, datetime.utcnow().isoformat(), str(user_id)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user total credits: {e}")
            return False
    
    # Job Management
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new processing job"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            job_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO processing_jobs (
                    id, user_id, api_key_id, job_type, status, input_config, 
                    processing_options, estimated_credits
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_data['user_id'],
                job_data['api_key_id'],
                job_data['job_type'],
                job_data.get('status', 'pending'),
                json.dumps(job_data['input_config']),
                json.dumps(job_data.get('processing_options', {})),
                job_data.get('estimated_credits', 0)
            ))
            
            conn.commit()
            conn.close()
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return None
    
    def get_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM processing_jobs WHERE id = ?", (str(job_id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                job = dict(row)
                # Parse JSON fields
                if job.get('input_config'):
                    job['input_config'] = json.loads(job['input_config'])
                if job.get('processing_options'):
                    job['processing_options'] = json.loads(job['processing_options'])
                return job
            return None
            
        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return None
    
    def update_job_status(self, job_id: UUID, status: JobStatus, error_message: str = None) -> bool:
        """Update job status"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_fields = ["status = ?", "updated_at = ?"]
            values = [status.value, datetime.utcnow().isoformat()]
            
            if status == JobStatus.PROCESSING:
                update_fields.append("started_at = ?")
                values.append(datetime.utcnow().isoformat())
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                update_fields.append("completed_at = ?")
                values.append(datetime.utcnow().isoformat())
            
            if error_message:
                update_fields.append("error_message = ?")
                values.append(error_message)
            
            values.append(str(job_id))
            
            cursor.execute(f"""
                UPDATE processing_jobs SET {', '.join(update_fields)} WHERE id = ?
            """, values)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE processing_jobs SET
                    status = ?,
                    completed_at = ?,
                    output_file_url = ?,
                    output_file_size = ?,
                    output_duration = ?,
                    actual_credits_used = ?,
                    updated_at = ?
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
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating job completion: {e}")
            return False

    def update_job_progress(self, job_id: UUID, progress_data: Dict[str, Any]) -> bool:
        """Update job progress data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Store progress as JSON
            progress_json = json.dumps(progress_data)

            cursor.execute("""
                UPDATE processing_jobs
                SET progress_data = ?, updated_at = ?
                WHERE id = ?
            """, (progress_json, datetime.utcnow().isoformat(), str(job_id)))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating job progress: {e}")
            return False

    def get_job_progress(self, job_id: UUID) -> Dict[str, Any]:
        """Get job progress data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT progress_data FROM processing_jobs WHERE id = ?
            """, (str(job_id),))

            row = cursor.fetchone()
            conn.close()

            if row and row['progress_data']:
                return json.loads(row['progress_data'])

            return {}

        except Exception as e:
            logger.error(f"Error getting job progress: {e}")
            return {}

    def get_user_jobs(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's jobs with pagination"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM processing_jobs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (str(user_id), limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            jobs = []
            for row in rows:
                job = dict(row)
                if job.get('input_config'):
                    job['input_config'] = json.loads(job['input_config'])
                if job.get('processing_options'):
                    job['processing_options'] = json.loads(job['processing_options'])
                jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting user jobs: {e}")
            return []
    
    def count_user_jobs(self, user_id: UUID) -> int:
        """Count user's total jobs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM processing_jobs WHERE user_id = ?", (str(user_id),))
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error counting user jobs: {e}")
            return 0
    
    # Statistics
    def count_total_jobs(self) -> int:
        """Count total jobs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM processing_jobs")
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error counting total jobs: {e}")
            return 0
    
    def count_active_jobs(self) -> int:
        """Count active jobs"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM processing_jobs 
                WHERE status IN ('pending', 'processing')
            """)
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error counting active jobs: {e}")
            return 0
    
    def check_rate_limit(self, api_key_id: UUID, endpoint: str, window_type: str, limit: int) -> bool:
        """Check if API key is within rate limits"""
        # For local testing, always return True
        return True
