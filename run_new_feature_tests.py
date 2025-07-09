#!/usr/bin/env python3
"""
Test runner for new features: hybrid storage, Azure storage, and admin APIs
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        'USE_SQLITE': 'true',
        'USE_LOCAL_STORAGE': 'true',
        'SUPABASE_URL': '',
        'SUPABASE_SERVICE_KEY': '',
        'ADMIN_API_KEY': 'test-admin-key',
        'AZURE_STORAGE_CONNECTION_STRING': 'DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net',
        'STORAGE_BUCKET': 'test-bucket',
        'LOCAL_STORAGE_PATH': '/tmp/test_storage',
        'TEMP_STORAGE_PATH': '/tmp/test_video_processing',
        'PYTHONPATH': str(Path.cwd()),
    }
    
    # Update environment
    os.environ.update(test_env)
    
    # Create test directories
    Path('/tmp/test_storage').mkdir(exist_ok=True)
    Path('/tmp/test_video_processing').mkdir(exist_ok=True)
    
    print("✅ Test environment setup complete")

def run_test_suite(test_file, description):
    """Run a specific test suite"""
    print(f"\n🧪 Running {description}...")
    print("=" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            test_file, 
            '-v', 
            '--tb=short',
            '--color=yes'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            print(f"   Tests run: {result.stdout.count('PASSED')}")
            if result.stdout.count('FAILED') > 0:
                print(f"   Failed: {result.stdout.count('FAILED')}")
        else:
            print(f"❌ {description} - FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False

def run_manual_tests():
    """Run manual tests for components that need special setup"""
    print("\n🔧 Running manual component tests...")
    print("=" * 60)
    
    # Test 1: Hybrid Storage Service
    try:
        print("Testing Hybrid Storage Service...")
        from services.storage_hybrid import HybridStorageService
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['LOCAL_STORAGE_PATH'] = temp_dir
            
            storage = HybridStorageService()
            
            # Test basic functionality
            test_file = Path(temp_dir) / "test.mp4"
            test_file.write_bytes(b"test content")
            
            # Test temp file upload
            result = storage.upload_temp_file(test_file, "temp_test.mp4")
            assert result is not None, "Temp file upload failed"
            
            # Test output file upload
            result = storage.upload_output_file(test_file, "output_test.mp4")
            assert result is not None, "Output file upload failed"
            
            # Test cleanup
            cleanup_count = storage.cleanup_temp_files(0)  # Clean all files
            assert cleanup_count >= 0, "Cleanup failed"
            
            # Test stats
            stats = storage.get_storage_stats()
            assert isinstance(stats, dict), "Stats retrieval failed"
            
        print("✅ Hybrid Storage Service - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Hybrid Storage Service - FAILED: {e}")
        return False

def test_azure_storage_mock():
    """Test Azure Storage with mocks"""
    print("Testing Azure Storage Service (mocked)...")
    
    try:
        # Mock Azure dependencies
        import sys
        from unittest.mock import Mock, patch
        
        # Create mock modules
        mock_azure = Mock()
        mock_azure.storage = Mock()
        mock_azure.storage.blob = Mock()
        mock_azure.core = Mock()
        mock_azure.core.exceptions = Mock()
        
        sys.modules['azure'] = mock_azure
        sys.modules['azure.storage'] = mock_azure.storage
        sys.modules['azure.storage.blob'] = mock_azure.storage.blob
        sys.modules['azure.core'] = mock_azure.core
        sys.modules['azure.core.exceptions'] = mock_azure.core.exceptions
        
        # Mock classes
        mock_azure.storage.blob.BlobServiceClient = Mock()
        mock_azure.storage.blob.BlobClient = Mock()
        mock_azure.core.exceptions.ResourceNotFoundError = Exception
        
        # Now test the service
        with patch('services.storage_azure.AZURE_AVAILABLE', True):
            from services.storage_azure import AzureStorageService
            
            # Mock the blob service client
            with patch('services.storage_azure.BlobServiceClient') as mock_client:
                mock_instance = Mock()
                mock_client.from_connection_string.return_value = mock_instance
                
                # Mock container operations
                mock_container = Mock()
                mock_instance.get_container_client.return_value = mock_container
                mock_container.get_container_properties.return_value = {"name": "test"}
                
                # Create service
                storage = AzureStorageService()
                assert storage.blob_service == mock_instance
                assert storage.container_name == "video-processing"
        
        print("✅ Azure Storage Service (mocked) - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Azure Storage Service (mocked) - FAILED: {e}")
        return False

def test_api_imports():
    """Test that API imports work correctly"""
    print("Testing API imports...")
    
    try:
        # Test main API imports
        from api.main import app
        assert app is not None, "FastAPI app import failed"
        
        # Test storage imports
        from services.storage_hybrid import HybridStorageService
        assert HybridStorageService is not None, "Hybrid storage import failed"
        
        # Test that the API uses hybrid storage
        from api import main
        assert hasattr(main, 'storage_service'), "Storage service not found in main"
        
        print("✅ API imports - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ API imports - FAILED: {e}")
        return False

def cleanup_test_environment():
    """Clean up test environment"""
    try:
        # Remove test directories
        test_dirs = ['/tmp/test_storage', '/tmp/test_video_processing']
        for test_dir in test_dirs:
            if Path(test_dir).exists():
                shutil.rmtree(test_dir)
        
        print("✅ Test environment cleanup complete")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

def main():
    """Main test runner"""
    print("🚀 Starting New Features Test Suite")
    print("Testing: Hybrid Storage, Azure Storage, Admin APIs")
    print("=" * 60)
    
    # Setup
    setup_test_environment()
    
    # Track results
    results = []
    
    # Test suites to run
    test_suites = [
        ("tests/test_storage_hybrid.py", "Hybrid Storage Unit Tests"),
        ("tests/test_storage_azure.py", "Azure Storage Unit Tests"),
        ("tests/test_api_admin_endpoints.py", "Admin API Endpoints Tests"),
        ("tests/test_integration_hybrid_storage.py", "Hybrid Storage Integration Tests"),
    ]
    
    # Run pytest suites
    for test_file, description in test_suites:
        if Path(test_file).exists():
            success = run_test_suite(test_file, description)
            results.append((description, success))
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results.append((description, False))
    
    # Run manual tests
    manual_tests = [
        ("Hybrid Storage Manual Test", run_manual_tests),
        ("Azure Storage Mock Test", test_azure_storage_mock),
        ("API Imports Test", test_api_imports),
    ]
    
    for description, test_func in manual_tests:
        success = test_func()
        results.append((description, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description:<40} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")
    
    # Cleanup
    cleanup_test_environment()
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! New features are ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review and fix issues before deployment.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
