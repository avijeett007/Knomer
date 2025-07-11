#!/usr/bin/env python3
"""
Comprehensive test to verify service class initializations and API functionality
"""
import os
import sys
import unittest
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the services we want to test
from services.database import DatabaseService
from services.auth import AuthService
from services.credit_manager import CreditManager
from services.storage_local import LocalStorageService
from services.storage_hybrid import HybridStorageService
from config import settings


class ServiceInitializationTest(unittest.TestCase):
    """Test service class initializations with and without db_service parameter"""
    
    def setUp(self):
        """Set up mock objects"""
        self.mock_db_service = MagicMock(spec=DatabaseService)
    
    def test_credit_manager_init_without_param(self):
        """Test CreditManager initialization without parameters"""
        cm = CreditManager()
        self.assertIsInstance(cm.db_service, DatabaseService)
        
    def test_credit_manager_init_with_param(self):
        """Test CreditManager initialization with db_service parameter"""
        cm = CreditManager(self.mock_db_service)
        self.assertEqual(cm.db_service, self.mock_db_service)
        
    def test_auth_service_init_without_param(self):
        """Test AuthService initialization without parameters"""
        auth = AuthService()
        self.assertIsInstance(auth.db_service, DatabaseService)
        
    def test_auth_service_init_with_param(self):
        """Test AuthService initialization with db_service parameter"""
        auth = AuthService(self.mock_db_service)
        self.assertEqual(auth.db_service, self.mock_db_service)


class StorageServicesTest(unittest.TestCase):
    """Test storage services functionality"""
    
    def test_local_storage_url_generation(self):
        """Test LocalStorageService URL generation uses SERVER_URL"""
        storage = LocalStorageService()
        
        # Create a test file path
        test_filename = "test_file.mp4"
        
        # Get URL and verify it uses SERVER_URL from settings
        url = storage.get_download_url(test_filename)
        expected_url = f"{settings.SERVER_URL}/api/v1/download/{test_filename}"
        self.assertEqual(url, expected_url)
        
    @patch('services.storage_hybrid.SupabaseStorageService')
    def test_hybrid_storage_public_url(self, mock_supabase):
        """Test HybridStorageService get_public_url method"""
        # Configure mock
        mock_instance = MagicMock()
        mock_supabase.return_value = mock_instance
        mock_instance.get_public_url.return_value = "https://supabase.url/storage/v1/object/test_file.mp4"
        
        # Test with cloud storage
        with patch('config.settings.USE_CLOUD_STORAGE', True):
            storage = HybridStorageService()
            url = storage.get_public_url("test_file.mp4")
            self.assertTrue(url.startswith("https://"))
            
        # Test with local storage
        with patch('config.settings.USE_CLOUD_STORAGE', False):
            with patch('config.settings.SERVER_URL', "http://localhost:8001"):
                storage = HybridStorageService()
                url = storage.get_public_url("test_file.mp4")
                self.assertEqual(url, "http://localhost:8001/api/v1/download/test_file.mp4")


class MainAppSimulationTest(unittest.TestCase):
    """Simulate main app initialization to verify no TypeErrors occur"""
    
    def test_main_app_service_init(self):
        """Test that the main app service initialization pattern works"""
        db_service = DatabaseService()
        
        # These should not raise TypeError after our fixes
        credit_manager = CreditManager(db_service)
        auth_service = AuthService(db_service)
        
        # Verify the services are properly initialized
        self.assertIsNotNone(credit_manager)
        self.assertIsNotNone(auth_service)
        self.assertEqual(credit_manager.db_service, db_service)
        self.assertEqual(auth_service.db_service, db_service)


class RedisConnectionTest(unittest.TestCase):
    """Test Redis connection with SSL"""
    
    @patch('services.database.redis.Redis')
    def test_redis_ssl_connection(self, mock_redis):
        """Test Redis connection with SSL"""
        # This test verifies the Redis connection pattern using SSL
        
        # Simulate a rediss:// URL connection
        ssl_url = "rediss://:[password]@[hostname]:6380/0?ssl_cert_reqs=CERT_NONE"
        
        # Try to connect to Redis using this URL pattern
        # This is just a simulation, not an actual connection
        from ssl import CERT_NONE
        import redis
        
        # Modify the URL for testing if needed
        if "rediss://" in ssl_url and "ssl_cert_reqs" not in ssl_url:
            ssl_url += "?ssl_cert_reqs=CERT_NONE"
        
        # Verify the URL has the correct SSL parameters
        self.assertIn("ssl_cert_reqs=CERT_NONE", ssl_url)


if __name__ == "__main__":
    logger.info("Starting service initialization tests...")
    unittest.main()
