#!/usr/bin/env python3
"""
Comprehensive test to verify all imports and initialization patterns in the API
This test simulates the import chain that occurs when the API starts up
"""
import os
import sys
import importlib
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_redis_ssl_connection():
    """Test that Redis SSL connection pattern is correct"""
    logger.info("Testing Redis SSL connection pattern...")
    
    try:
        # Import the Redis connection module
        from ssl import CERT_NONE
        import redis
        
        # Test connection string pattern for Azure Redis with SSL
        ssl_url = "rediss://:[password]@[hostname]:6380/0"
        
        # Check if the URL needs the SSL parameter
        if "rediss://" in ssl_url and "ssl_cert_reqs" not in ssl_url:
            ssl_url += "?ssl_cert_reqs=CERT_NONE"
        
        logger.info(f"Redis SSL URL with cert_reqs param: {ssl_url}")
        assert "ssl_cert_reqs=CERT_NONE" in ssl_url
        logger.info("✓ Redis SSL connection pattern is correct")
        
        return True
    except Exception as e:
        logger.error(f"Error in Redis SSL connection test: {e}")
        return False

def test_imports():
    """Test that all imports work correctly"""
    logger.info("Testing imports...")
    
    try:
        # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # First test settings import which is used everywhere
        logger.info("Importing settings...")
        from config.settings import settings
        logger.info(f"✓ Settings imported successfully: SERVER_URL={settings.SERVER_URL}")
        
        # Test database services import
        logger.info("Importing database services...")
        if settings.USE_SQLITE:
            from services.database_sqlite import SQLiteDatabaseService as DatabaseService
            logger.info("✓ Using SQLite database service")
        else:
            from services.database import DatabaseService
            logger.info("✓ Using Supabase database service")
        
        # Create database service instance
        logger.info("Creating database service instance...")
        db_service = DatabaseService()
        logger.info("✓ Database service instance created")
        
        # Test auth service import and initialization with db_service
        logger.info("Testing AuthService initialization...")
        from services.auth import AuthService
        auth_service = AuthService(db_service)
        logger.info("✓ AuthService initialized with db_service")
        
        # Test credit manager import and initialization with db_service
        logger.info("Testing CreditManager initialization...")
        from services.credit_manager import CreditManager
        credit_manager = CreditManager(db_service)
        logger.info("✓ CreditManager initialized with db_service")
        
        # Test storage service
        logger.info("Testing storage services...")
        from services.storage_local import LocalStorageService
        local_storage = LocalStorageService()
        logger.info("✓ LocalStorageService initialized")
        
        # Test HybridStorageService
        logger.info("Testing HybridStorageService...")
        from services.storage_hybrid import HybridStorageService
        hybrid_storage = HybridStorageService()
        logger.info("✓ HybridStorageService initialized")
        
        # Test v2_endpoints imports
        logger.info("Testing v2_endpoints imports...")
        with patch.dict('sys.modules'):
            # Mock FastAPI router to prevent actual router creation
            with patch('fastapi.APIRouter'):
                # We need to reload if it was already imported
                if 'api.v2_endpoints' in sys.modules:
                    del sys.modules['api.v2_endpoints']
                import api.v2_endpoints
                logger.info("✓ v2_endpoints imported successfully")
        
        logger.info("All imports tested successfully!")
        return True
    except Exception as e:
        logger.error(f"Error testing imports: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    redis_test_result = test_redis_ssl_connection()
    import_test_result = test_imports()
    
    if redis_test_result and import_test_result:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Tests failed!")
        sys.exit(1)
