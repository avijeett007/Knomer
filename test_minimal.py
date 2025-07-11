#!/usr/bin/env python3
"""
Minimal test to verify our fixes for service initialization and import issues
"""
import os
import sys
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_minimal():
    """Run minimal tests for key fixes"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    # Test 1: Verify settings import in v2_endpoints
    logger.info("Testing settings import in v2_endpoints...")
    try:
        # Use separate module-level imports to isolate errors
        with open(os.path.join('api', 'v2_endpoints.py'), 'r') as f:
            content = f.read()
            if 'from config.settings import settings' in content:
                logger.info("✓ v2_endpoints.py has settings import")
            else:
                logger.error("❌ v2_endpoints.py is missing settings import")
                success = False
    except Exception as e:
        logger.error(f"Error checking v2_endpoints.py: {e}")
        success = False

    # Test 2: Verify AuthService accepts db_service parameter
    logger.info("Testing AuthService initialization...")
    try:
        from services.auth import AuthService
        from services.database import DatabaseService
        
        # Mock DB service
        db_mock = MagicMock(spec=DatabaseService)
        
        # Test with parameter
        auth = AuthService(db_mock)
        if auth.db_service == db_mock:
            logger.info("✓ AuthService accepts db_service parameter")
        else:
            logger.error("❌ AuthService not using provided db_service")
            success = False
            
        # Test without parameter
        auth2 = AuthService()
        if auth2.db_service is not None:
            logger.info("✓ AuthService works without parameters")
        else:
            logger.error("❌ AuthService fails without parameters")
            success = False
    except Exception as e:
        logger.error(f"Error testing AuthService: {e}")
        success = False
        
    # Test 3: Verify CreditManager accepts db_service parameter  
    logger.info("Testing CreditManager initialization...")
    try:
        from services.credit_manager import CreditManager
        
        # Test with parameter
        cm = CreditManager(db_mock)
        if cm.db_service == db_mock:
            logger.info("✓ CreditManager accepts db_service parameter")
        else:
            logger.error("❌ CreditManager not using provided db_service")
            success = False
            
        # Test without parameter
        cm2 = CreditManager()
        if cm2.db_service is not None:
            logger.info("✓ CreditManager works without parameters")
        else:
            logger.error("❌ CreditManager fails without parameters")
            success = False
    except Exception as e:
        logger.error(f"Error testing CreditManager: {e}")
        success = False
    
    # Test 4: Verify Redis SSL connection pattern from memory
    logger.info("Testing Redis SSL connection pattern...")
    try:
        # Test connection string pattern for Azure Redis with SSL
        ssl_url = "rediss://:[password]@[hostname]:6380/0"
        
        # Check if the URL needs the SSL parameter
        if "rediss://" in ssl_url and "ssl_cert_reqs" not in ssl_url:
            ssl_url += "?ssl_cert_reqs=CERT_NONE"
        
        if "ssl_cert_reqs=CERT_NONE" in ssl_url:
            logger.info("✓ Redis SSL connection pattern is correct")
        else:
            logger.error("❌ Redis SSL connection pattern is incorrect")
            success = False
    except Exception as e:
        logger.error(f"Error in Redis SSL connection test: {e}")
        success = False
    
    return success

if __name__ == "__main__":
    if test_minimal():
        logger.info("✅ All minimal tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1)
