#!/usr/bin/env python3
"""
Simple test to verify service class initialization fixes
"""
import os
import sys
import logging
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_services():
    """Test that our service classes can be initialized both ways"""
    logger.info("Testing service initialization...")
    
    # Mock the DatabaseService to avoid actual DB connections
    mock_db = MagicMock()
    mock_db.get_api_key_by_hash.return_value = {"is_active": True, "user_id": "test-uuid"}
    
    try:
        # Import services (will work even if pydantic-settings is not installed)
        logger.info("Importing services...")
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import and test the AuthService class
        from services.auth import AuthService
        logger.info("Testing AuthService...")
        
        # Test default initialization
        auth1 = AuthService()
        logger.info("✓ AuthService initialized without parameters")
        
        # Test with db_service parameter
        auth2 = AuthService(mock_db)
        logger.info("✓ AuthService initialized with db_service parameter")
        
        # Import and test CreditManager
        from services.credit_manager import CreditManager
        logger.info("Testing CreditManager...")
        
        # Test default initialization
        cm1 = CreditManager()
        logger.info("✓ CreditManager initialized without parameters")
        
        # Test with db_service parameter
        cm2 = CreditManager(mock_db)
        logger.info("✓ CreditManager initialized with db_service parameter")
        
        # Simulate main.py initialization pattern
        logger.info("Simulating main.py initialization pattern...")
        auth_service = AuthService(mock_db)
        credit_manager = CreditManager(mock_db)
        logger.info("✓ Main app service initialization pattern works correctly")
        
        return True
    except Exception as e:
        logger.error(f"Error testing services: {e}")
        return False

if __name__ == "__main__":
    success = test_services()
    if success:
        logger.info("All service initialization tests passed!")
        sys.exit(0)
    else:
        logger.error("Service initialization tests failed!")
        sys.exit(1)
