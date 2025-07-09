"""
SQLite database setup for local testing
"""
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
import uuid

def create_sqlite_schema(db_path: str):
    """Create SQLite database with schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'basic', 'premium', 'enterprise'))
        )
    """)
    
    # API Keys table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            name TEXT,
            is_active BOOLEAN DEFAULT 1,
            last_used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            rate_limit_per_minute INTEGER DEFAULT 10,
            rate_limit_per_hour INTEGER DEFAULT 100,
            rate_limit_per_day INTEGER DEFAULT 1000
        )
    """)
    
    # User credits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_credits (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            total_credits INTEGER DEFAULT 0,
            used_credits INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)
    
    # Credit transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'bonus')),
            amount INTEGER NOT NULL,
            description TEXT,
            job_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Processing jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            api_key_id TEXT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
            job_type TEXT NOT NULL CHECK (job_type IN ('simple_merge', 'transition_merge', 'auto_effects', 'logo_overlay', 'multi_video', 'premium_ai_enhancement', 'audio_separation')),
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
            priority INTEGER DEFAULT 0,
            input_config TEXT NOT NULL,
            processing_options TEXT,
            estimated_credits INTEGER,
            actual_credits_used INTEGER,
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            output_file_url TEXT,
            output_file_size INTEGER,
            output_duration REAL,
            download_count INTEGER DEFAULT 0,
            first_downloaded_at TEXT,
            last_downloaded_at TEXT,
            download_expires_at TEXT,
            progress_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Video files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_files (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
            file_type TEXT NOT NULL CHECK (file_type IN ('input', 'output', 'intermediate', 'transition')),
            file_url TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            duration REAL,
            resolution TEXT,
            format TEXT,
            order_index INTEGER,
            is_temporary BOOLEAN DEFAULT 0,
            cleanup_after TEXT,
            cleaned_up_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Rate limits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id TEXT PRIMARY KEY,
            api_key_id TEXT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL,
            window_start TEXT NOT NULL,
            window_type TEXT NOT NULL CHECK (window_type IN ('minute', 'hour', 'day')),
            request_count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(api_key_id, endpoint, window_start, window_type)
        )
    """)
    
    # Processing templates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            template_type TEXT NOT NULL,
            configuration TEXT NOT NULL,
            credit_cost INTEGER NOT NULL,
            is_public BOOLEAN DEFAULT 0,
            created_by TEXT REFERENCES users(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_jobs_user_id ON processing_jobs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_files_job_id ON video_files(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id)")
    
    conn.commit()
    conn.close()
    print(f"✅ SQLite database created at {db_path}")

def seed_test_data(db_path: str):
    """Seed database with test data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test user
    user_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO users (id, email, name, subscription_tier, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "test@example.com", "Test User", "premium", 1))
    
    # Generate API key
    api_key = f"vp_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:10]
    api_key_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, is_active, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (api_key_id, user_id, key_hash, key_prefix, "Test API Key", 1, 100, 1000, 10000))
    
    # Add credits
    credits_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO user_credits (id, user_id, total_credits, used_credits)
        VALUES (?, ?, ?, ?)
    """, (credits_id, user_id, 10000, 0))  # 10,000 test credits
    
    # Add credit transaction
    transaction_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO credit_transactions (id, user_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?, ?)
    """, (transaction_id, user_id, "bonus", 10000, "Initial test credits"))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Test data seeded successfully")
    print(f"📧 Test user email: test@example.com")
    print(f"🔑 Test API key: {api_key}")
    print(f"💰 Test credits: 10,000")
    
    return {
        "user_id": user_id,
        "api_key": api_key,
        "email": "test@example.com"
    }

def setup_local_database():
    """Setup local SQLite database for testing"""
    db_dir = Path(__file__).parent
    db_path = db_dir / "test_database.db"
    
    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        print("🗑️  Removed existing database")
    
    # Create new database
    create_sqlite_schema(str(db_path))
    test_data = seed_test_data(str(db_path))
    
    print(f"\n🎉 Local database setup complete!")
    print(f"Database path: {db_path}")
    print(f"Connection string: sqlite:///{db_path}")
    
    return test_data

if __name__ == "__main__":
    setup_local_database()
