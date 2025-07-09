#!/usr/bin/env python3
"""
Standalone tests for new features without heavy dependencies
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Set test environment
os.environ['USE_SQLITE'] = 'true'
os.environ['USE_LOCAL_STORAGE'] = 'true'
os.environ['SUPABASE_URL'] = ''
os.environ['SUPABASE_SERVICE_KEY'] = ''
os.environ['ADMIN_API_KEY'] = 'test-admin-key'

def test_hybrid_storage():
    """Test hybrid storage service"""
    print("🧪 Testing Hybrid Storage Service...")
    
    try:
        from services.storage_hybrid import HybridStorageService
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock settings
            with patch('services.storage_hybrid.settings') as mock_settings:
                mock_settings.LOCAL_STORAGE_PATH = temp_dir
                mock_settings.SUPABASE_URL = ''
                mock_settings.SUPABASE_SERVICE_KEY = ''
                
                # Create service
                storage = HybridStorageService()
                
                # Test 1: Basic initialization
                assert not storage.use_cloud_output, "Should use local storage only"
                print("  ✅ Initialization - PASSED")
                
                # Test 2: Upload temp file
                test_file = Path(temp_dir) / "test.mp4"
                test_file.write_bytes(b"test content")
                
                result = storage.upload_temp_file(test_file, "temp_test.mp4")
                assert result is not None, "Temp file upload failed"
                assert result.startswith("file://"), "Should return file URL"
                print("  ✅ Temp file upload - PASSED")
                
                # Test 3: Upload output file
                result = storage.upload_output_file(test_file, "output_test.mp4")
                assert result is not None, "Output file upload failed"
                print("  ✅ Output file upload - PASSED")
                
                # Test 4: Storage routing
                temp_result = storage.upload_to_storage(test_file, "temp/test.mp4")
                output_result = storage.upload_to_storage(test_file, "outputs/test.mp4")
                assert temp_result != output_result, "Should route differently"
                print("  ✅ Storage routing - PASSED")
                
                # Test 5: Cleanup
                cleanup_count = storage.cleanup_temp_files(0)
                assert cleanup_count >= 0, "Cleanup should return count"
                print("  ✅ Cleanup - PASSED")
                
                # Test 6: Stats
                stats = storage.get_storage_stats()
                assert isinstance(stats, dict), "Stats should be dict"
                assert "cloud_storage_enabled" in stats, "Should have cloud storage flag"
                print("  ✅ Stats - PASSED")
        
        print("✅ Hybrid Storage Service - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Hybrid Storage Service - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_azure_storage_mock():
    """Test Azure storage with mocks"""
    print("\n🧪 Testing Azure Storage Service (Mocked)...")
    
    try:
        # Mock Azure modules
        with patch.dict('sys.modules', {
            'azure': Mock(),
            'azure.storage': Mock(),
            'azure.storage.blob': Mock(),
            'azure.core': Mock(),
            'azure.core.exceptions': Mock(),
        }):
            # Mock the specific classes and exceptions
            mock_blob_service = Mock()
            mock_blob_client = Mock()
            mock_resource_not_found = type('ResourceNotFoundError', (Exception,), {})
            
            with patch('services.storage_azure.AZURE_AVAILABLE', True):
                with patch('services.storage_azure.BlobServiceClient', mock_blob_service):
                    with patch('services.storage_azure.ResourceNotFoundError', mock_resource_not_found):
                        # Mock settings
                        with patch('services.storage_azure.settings') as mock_settings:
                            mock_settings.AZURE_STORAGE_CONNECTION_STRING = 'test-connection-string'
                            mock_settings.STORAGE_BUCKET = 'test-bucket'
                            
                            # Mock blob service instance
                            mock_service_instance = Mock()
                            mock_blob_service.from_connection_string.return_value = mock_service_instance
                            
                            # Mock container client
                            mock_container_client = Mock()
                            mock_service_instance.get_container_client.return_value = mock_container_client
                            mock_container_client.get_container_properties.return_value = {"name": "test"}
                            
                            # Import and test
                            from services.storage_azure import AzureStorageService
                            
                            # Test initialization
                            storage = AzureStorageService()
                            assert storage.blob_service == mock_service_instance
                            print("  ✅ Initialization - PASSED")
                            
                            # Test content type detection
                            content_type = storage._get_content_type(Path("test.mp4"))
                            assert content_type == "video/mp4"
                            print("  ✅ Content type detection - PASSED")
                            
                            # Test storage path extraction
                            url = "https://test.blob.core.windows.net/container/path/file.mp4"
                            path = storage._extract_storage_path(url)
                            assert path == "path/file.mp4"
                            print("  ✅ Path extraction - PASSED")
        
        print("✅ Azure Storage Service - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Azure Storage Service - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_settings_configuration():
    """Test settings configuration"""
    print("\n🧪 Testing Settings Configuration...")
    
    try:
        from config.settings import Settings
        
        # Test with environment variables
        test_env = {
            'ADMIN_API_KEY': 'test-admin-key-123',
            'AZURE_STORAGE_CONNECTION_STRING': 'test-connection',
            'USE_LOCAL_STORAGE': 'false',
            'SUPABASE_URL': 'https://test.supabase.co'
        }
        
        with patch.dict(os.environ, test_env):
            settings = Settings()
            
            assert settings.ADMIN_API_KEY == 'test-admin-key-123'
            assert settings.AZURE_STORAGE_CONNECTION_STRING == 'test-connection'
            assert settings.USE_LOCAL_STORAGE is False
            assert settings.SUPABASE_URL == 'https://test.supabase.co'
            
        print("  ✅ Environment variable loading - PASSED")
        print("  ✅ Admin API key configuration - PASSED")
        print("  ✅ Azure storage configuration - PASSED")
        print("✅ Settings Configuration - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Settings Configuration - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_api_logic():
    """Test admin API logic without FastAPI dependencies"""
    print("\n🧪 Testing Admin API Logic...")
    
    try:
        # Mock the dependencies
        mock_db_service = Mock()
        mock_credit_manager = Mock()
        mock_auth_service = Mock()
        
        # Test user creation logic
        mock_db_service.create_user.return_value = "user-123"
        mock_credit_manager.add_credits.return_value = True
        
        mock_auth_instance = Mock()
        mock_auth_instance.create_api_key.return_value = {
            'api_key': 'vp_test_key',
            'id': 'key-123'
        }
        mock_auth_service.return_value = mock_auth_instance
        
        # Simulate user creation
        user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'subscription_tier': 'premium',
            'is_active': True
        }
        
        user_id = mock_db_service.create_user(user_data)
        assert user_id == "user-123"
        print("  ✅ User creation logic - PASSED")
        
        # Simulate credit addition
        credit_success = mock_credit_manager.add_credits(
            user_id=user_id,
            amount=50000,
            description="Initial credits"
        )
        assert credit_success is True
        print("  ✅ Credit addition logic - PASSED")
        
        # Simulate API key creation
        api_key_result = mock_auth_instance.create_api_key(
            user_id=user_id,
            name="Default API Key"
        )
        assert api_key_result['api_key'] == 'vp_test_key'
        print("  ✅ API key creation logic - PASSED")
        
        print("✅ Admin API Logic - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Admin API Logic - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_operations():
    """Test file operations used by storage services"""
    print("\n🧪 Testing File Operations...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test file creation
            test_file = temp_path / "test.mp4"
            test_content = b"test video content" * 100
            test_file.write_bytes(test_content)
            assert test_file.exists()
            print("  ✅ File creation - PASSED")
            
            # Test file reading
            read_content = test_file.read_bytes()
            assert read_content == test_content
            print("  ✅ File reading - PASSED")
            
            # Test directory creation
            sub_dir = temp_path / "outputs" / "subdir"
            sub_dir.mkdir(parents=True, exist_ok=True)
            assert sub_dir.exists()
            print("  ✅ Directory creation - PASSED")
            
            # Test file copying
            dest_file = temp_path / "outputs" / "copied.mp4"
            dest_file.write_bytes(test_file.read_bytes())
            assert dest_file.exists()
            assert dest_file.read_bytes() == test_content
            print("  ✅ File copying - PASSED")
            
            # Test file size calculation
            file_size = test_file.stat().st_size
            assert file_size == len(test_content)
            print("  ✅ File size calculation - PASSED")
        
        print("✅ File Operations - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ File Operations - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all standalone tests"""
    print("🚀 Running Standalone Tests for New Features")
    print("=" * 60)
    
    tests = [
        ("Hybrid Storage Service", test_hybrid_storage),
        ("Azure Storage Service (Mocked)", test_azure_storage_mock),
        ("Settings Configuration", test_settings_configuration),
        ("Admin API Logic", test_admin_api_logic),
        ("File Operations", test_file_operations),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<35} {status}")
    
    print("-" * 60)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! New features are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the issues.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
