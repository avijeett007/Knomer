#!/usr/bin/env python3
"""
Critical imports and initialization checker for Knomer API
This script focuses specifically on:
1. Import errors in key modules
2. Service initialization issues
3. Redis SSL configuration

This script is designed to work without requiring external dependencies like celery
"""
import importlib
import logging
import os
import sys
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Service classes to check initialization
SERVICE_CLASSES = [
    ('services.auth', 'AuthService'),
    ('services.credit_manager', 'CreditManager'),
    ('services.storage_local', 'LocalStorageService'),
    ('services.storage_hybrid', 'HybridStorageService')
]

# Key modules to check for import errors
KEY_MODULES = [
    'config.settings',
    'api.v2_endpoints',  # Don't check main.py as it requires celery
    'services.database',
    'services.auth',
    'services.credit_manager',
    'services.storage_local',
    'services.storage_hybrid'
]

def check_service_init():
    """Check if service classes initialize properly"""
    all_passed = True
    mock_db = MagicMock()
    
    for module_name, class_name in SERVICE_CLASSES:
        try:
            # Import the module and class
            module = importlib.import_module(module_name)
            class_obj = getattr(module, class_name)
            
            # Test initialization with and without parameters
            obj_default = class_obj()
            logger.info(f"✓ {class_name} initializes without parameters")
            
            # If it has a db_service attribute, test with mock
            if hasattr(obj_default, 'db_service'):
                obj_with_param = class_obj(db_service=mock_db)
                if obj_with_param.db_service == mock_db:
                    logger.info(f"✓ {class_name} accepts and uses db_service parameter")
                else:
                    logger.warning(f"⚠️ {class_name} accepts but doesn't use db_service parameter")
                    
        except Exception as e:
            logger.error(f"❌ Error initializing {class_name}: {e}")
            all_passed = False
    
    return all_passed

def check_module_imports():
    """Check if key modules import successfully"""
    all_passed = True
    
    for module_name in KEY_MODULES:
        try:
            module = importlib.import_module(module_name)
            logger.info(f"✓ Successfully imported {module_name}")
        except Exception as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
            all_passed = False
    
    return all_passed

def check_missing_imports_in_files():
    """Check for common import issues in key files"""
    all_passed = True
    
    # Key files and the imports they should have
    files_to_check = {
        'api/v2_endpoints.py': ['import os', 'from config.settings import settings'],
        'services/auth.py': ['from config.settings import settings'],
        'services/credit_manager.py': ['from config.settings import settings']
    }
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    for file_path, required_imports in files_to_check.items():
        abs_path = os.path.join(root_dir, file_path)
        if not os.path.exists(abs_path):
            logger.warning(f"⚠️ File not found: {file_path}")
            continue
            
        with open(abs_path, 'r') as f:
            content = f.read()
            
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
        
        if missing_imports:
            logger.error(f"❌ {file_path} is missing imports: {', '.join(missing_imports)}")
            all_passed = False
        else:
            logger.info(f"✓ {file_path} has all required imports")
    
    return all_passed

def check_redis_ssl_config():
    """Verify Redis configuration is compatible with Azure Redis SSL"""
    # Look for Redis URL in settings
    try:
        from config.settings import settings
        redis_url = getattr(settings, 'REDIS_URL', None)
        
        if redis_url and 'rediss://' in redis_url:
            # Check if it has the SSL cert parameter
            if 'ssl_cert_reqs=CERT_NONE' not in redis_url:
                logger.warning(f"⚠️ Redis SSL URL is missing ssl_cert_reqs=CERT_NONE parameter")
                logger.info(f"  Current: {redis_url}")
                logger.info(f"  Recommended: {redis_url}?ssl_cert_reqs=CERT_NONE")
                return False
            else:
                logger.info("✓ Redis SSL configuration is correct")
        else:
            logger.info("✓ Not using Redis SSL (rediss://)")
            
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Redis configuration: {e}")
        return False

def check_for_undefined_settings():
    """Check for undefined settings variables in key files"""
    all_passed = True
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    directories = ['api', 'services']
    
    for directory in directories:
        dir_path = os.path.join(root_dir, directory)
        if os.path.exists(dir_path):
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, root_dir)
                        
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        # Check for settings usage without import
                        if 'settings.' in content and 'import settings' not in content.lower() and 'from config.settings import settings' not in content:
                            logger.warning(f"⚠️ {rel_path} uses settings but may be missing proper import")
                            all_passed = False
                            
    return all_passed

def prepare_redis_url_function():
    """Check if prepare_redis_url function exists for Azure Redis SSL support"""
    try:
        celery_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'celery_app.py')
        
        if os.path.exists(celery_app_path):
            with open(celery_app_path, 'r') as f:
                content = f.read()
                
            if 'def prepare_redis_url' in content and 'ssl_cert_reqs=CERT_NONE' in content:
                logger.info("✓ Found prepare_redis_url function for Redis SSL handling")
            else:
                logger.warning("""⚠️ Redis SSL handling function may be missing in celery_app.py
Consider adding:
def prepare_redis_url(url):
    \"\"\"Add SSL parameters to Redis URL if needed\"\"\"
    if url and url.startswith('rediss://') and 'ssl_cert_reqs' not in url:
        from ssl import CERT_NONE
        url = f"{url}?ssl_cert_reqs=CERT_NONE"
    return url""")
        else:
            logger.info("celery_app.py not found, skipping Redis SSL function check")
        
        return True
    except Exception as e:
        logger.error(f"Error checking Redis SSL function: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("KNOMER API CRITICAL IMPORTS & INITIALIZATION CHECK")
    print("=" * 80)
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(project_root)
    
    # Track overall success
    results = {
        "Module Imports": check_module_imports(),
        "Required File Imports": check_missing_imports_in_files(),
        "Service Initialization": check_service_init(),
        "Redis SSL Config": check_redis_ssl_config(),
        "Settings Usage": check_for_undefined_settings(),
        "Redis SSL Function": prepare_redis_url_function()
    }
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    all_passed = True
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "❌ FAIL"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL CRITICAL CHECKS PASSED!")
        print("Your API should initialize without errors.")
    else:
        print("⚠️ SOME CHECKS FAILED")
        print("Review the warnings and errors above before deploying.")
    print("=" * 80)
    
    sys.exit(0 if all_passed else 1)
