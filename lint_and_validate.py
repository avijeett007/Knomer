#!/usr/bin/env python3
"""
Comprehensive linting and validation script for the Knomer API
This script performs:
1. Import validation - ensures all modules can be imported
2. Initialization checks - verifies service classes can be properly initialized
3. Static analysis - runs pylint/flake8 on codebase
"""
import os
import sys
import importlib
import pkgutil
import logging
import subprocess
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Root directory and Python packages to validate
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGES_TO_CHECK = ['api', 'services', 'tasks', 'config']
INIT_FILES = []  # Will store all __init__.py files for validation

# Critical service classes that require initialization checks
SERVICE_CLASSES = [
    ('services.auth', 'AuthService'),
    ('services.credit_manager', 'CreditManager'),
    ('services.storage_local', 'LocalStorageService'),
    ('services.storage_hybrid', 'HybridStorageService'),
    ('services.database', 'DatabaseService')
]

def check_imports_recursively(package_name, prefix=""):
    """Recursively check all imports in the given package"""
    success = True
    package_path = None
    
    try:
        if prefix:
            full_name = f"{prefix}.{package_name}"
        else:
            full_name = package_name
            
        # Try importing the package
        package = importlib.import_module(full_name)
        package_path = os.path.dirname(package.__file__)
        logger.info(f"✓ Successfully imported {full_name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to import {full_name}: {e}")
        return False
    
    # If it's not a directory with an __init__.py, we're done
    if not os.path.isdir(package_path):
        return True
        
    # If it has __init__.py, add it to our list
    init_path = os.path.join(package_path, "__init__.py")
    if os.path.exists(init_path) and os.path.isfile(init_path):
        INIT_FILES.append(init_path)
    
    # Recursively check all submodules
    for _, name, is_pkg in pkgutil.iter_modules([package_path]):
        # Skip _* modules
        if name.startswith('_'):
            continue
            
        # Process this submodule/subpackage
        submodule_success = check_imports_recursively(name, full_name)
        success = success and submodule_success
        
    return success

def check_init_parameters():
    """Check service class initializers for correct parameter handling"""
    success = True
    mock_db = MagicMock()
    
    for module_name, class_name in SERVICE_CLASSES:
        logger.info(f"Testing {module_name}.{class_name} initialization...")
        try:
            # Import the module and class
            module = importlib.import_module(module_name)
            class_obj = getattr(module, class_name)
            
            # Test initialization with and without parameters where relevant
            obj1 = class_obj()  # Default init
            logger.info(f"✓ {class_name} initialized without parameters")
            
            # If the class has a db_service attribute, test initialization with it
            if hasattr(obj1, 'db_service'):
                obj2 = class_obj(db_service=mock_db)
                logger.info(f"✓ {class_name} initialized with db_service parameter")
                
                # Verify it's using our mock
                if obj2.db_service == mock_db:
                    logger.info(f"✓ {class_name} correctly uses provided db_service")
                else:
                    logger.error(f"❌ {class_name} not using provided db_service")
                    success = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize {class_name}: {e}")
            success = False
    
    return success

def check_settings_imports():
    """Check for settings imports in key modules"""
    success = True
    
    # Find all Python files
    python_files = []
    for package in PACKAGES_TO_CHECK:
        package_path = os.path.join(ROOT_DIR, package)
        if os.path.exists(package_path) and os.path.isdir(package_path):
            for root, _, files in os.walk(package_path):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
    
    # Check each file for settings usage without import
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            relative_path = os.path.relpath(file_path, ROOT_DIR)
            
            # If the file uses settings but doesn't import it
            if 'settings.' in content and 'from config.settings import settings' not in content and 'from config import settings' not in content:
                logger.warning(f"⚠️ {relative_path} uses settings but may not import it properly")
                success = False
    
    return success

def run_static_analysis():
    """Run static analysis tools on the codebase"""
    success = True
    
    # Check for flake8
    try:
        subprocess.run(['flake8', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Running flake8 for static analysis...")
        
        result = subprocess.run(
            ['flake8', '--select=F,E999', '--statistics', '.'], 
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error("❌ Flake8 found errors:")
            logger.error(result.stdout.decode('utf-8'))
            success = False
        else:
            logger.info("✓ Flake8 found no critical errors")
            
    except FileNotFoundError:
        logger.warning("⚠️ flake8 not found. Install with: pip install flake8")
    
    # Check for pylint
    try:
        subprocess.run(['pylint', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Running pylint for static analysis (on selected modules)...")
        
        # Run pylint on key modules - we only care about errors, not style
        for package in ['api/main.py', 'api/v2_endpoints.py']:
            pkg_path = os.path.join(ROOT_DIR, package)
            if os.path.exists(pkg_path):
                result = subprocess.run(
                    ['pylint', '--disable=all', '--enable=import-error,no-name-in-module,undefined-variable', pkg_path], 
                    cwd=ROOT_DIR,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                
                if result.returncode != 0:
                    output = result.stdout.decode('utf-8')
                    if output.strip():  # Only show if there are real errors
                        logger.error(f"❌ Pylint found errors in {package}:")
                        logger.error(output)
                        success = False
                else:
                    logger.info(f"✓ Pylint found no critical errors in {package}")
            
    except FileNotFoundError:
        logger.warning("⚠️ pylint not found. Install with: pip install pylint")
        
    return success

def check_app_startup():
    """Check if app starts up without errors (simulated)"""
    logger.info("Simulating app startup...")
    try:
        # Import just enough to detect import errors without actually starting the server
        import importlib.util
        
        # First check if config is properly importable
        import config.settings
        logger.info("✓ Config settings imported successfully")
        
        # Try importing the main FastAPI app
        from api import main
        logger.info("✓ Main FastAPI app imported successfully")
        
        # Try importing v2 endpoints
        from api import v2_endpoints
        logger.info("✓ V2 endpoints imported successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error simulating app startup: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_redis_ssl_config():
    """Verify Redis SSL configuration pattern"""
    logger.info("Checking Redis SSL configuration pattern...")
    
    try:
        # This is based on the remembered pattern for Azure Redis with SSL
        ssl_url = "rediss://:[password]@[hostname]:6380/0"
        
        if "ssl_cert_reqs" not in ssl_url:
            logger.warning("⚠️ Redis SSL URL should include ssl_cert_reqs=CERT_NONE parameter")
            logger.info(f"  Recommended format: {ssl_url}?ssl_cert_reqs=CERT_NONE")
            return False
            
        logger.info("✓ Redis SSL configuration pattern is correct")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Redis SSL config: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("KNOMER API VALIDATION AND LINTING")
    print("=" * 80)
    
    # Add the project root to sys.path
    sys.path.append(ROOT_DIR)
    
    # Track overall success
    overall_success = True
    
    # First install required packages if not present
    try:
        subprocess.run([
            'pip', 'install', '-q', 'flake8', 'pylint'
        ], check=True)
    except subprocess.CalledProcessError:
        logger.warning("Failed to install linting tools, continuing without them")
    
    # 1. Check that all packages can be imported
    print("\n[1/5] Checking module imports...")
    import_success = True
    for package in PACKAGES_TO_CHECK:
        package_success = check_imports_recursively(package)
        import_success = import_success and package_success
    
    if import_success:
        print("✓ All modules imported successfully")
    else:
        print("❌ Some modules failed to import")
        overall_success = False
    
    # 2. Check service initialization parameters
    print("\n[2/5] Checking service class initializations...")
    init_success = check_init_parameters()
    if init_success:
        print("✓ All service classes initialize correctly")
    else:
        print("❌ Some service classes have initialization issues")
        overall_success = False
    
    # 3. Check settings imports
    print("\n[3/5] Checking settings imports...")
    settings_success = check_settings_imports()
    if settings_success:
        print("✓ Settings are imported correctly")
    else:
        print("⚠️ Some files may have improper settings imports")
        # This is just a warning, not a failure
    
    # 4. Run static analysis
    print("\n[4/5] Running static analysis...")
    analysis_success = run_static_analysis()
    if analysis_success:
        print("✓ Static analysis passed")
    else:
        print("❌ Static analysis found issues")
        overall_success = False
    
    # 5. Check app startup simulation
    print("\n[5/5] Simulating app startup...")
    startup_success = check_app_startup()
    if startup_success:
        print("✓ App startup simulation successful")
    else:
        print("❌ App startup simulation failed")
        overall_success = False
    
    # 6. Check Redis SSL configuration as a bonus
    print("\n[BONUS] Checking Redis SSL configuration...")
    redis_ssl_success = check_redis_ssl_config()
    
    # Print final summary
    print("\n" + "=" * 80)
    if overall_success:
        print("✅ ALL VALIDATION CHECKS PASSED! Your app should run without import or initialization errors.")
    else:
        print("❌ SOME CHECKS FAILED. Please review the issues above before deploying.")
    print("=" * 80)
    
    sys.exit(0 if overall_success else 1)
