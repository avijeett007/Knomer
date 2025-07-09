#!/usr/bin/env python3
"""
Focused test for API endpoints without heavy dependencies
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Set test environment
os.environ['USE_SQLITE'] = 'true'
os.environ['USE_LOCAL_STORAGE'] = 'true'
os.environ['SUPABASE_URL'] = ''
os.environ['SUPABASE_SERVICE_KEY'] = ''
os.environ['ADMIN_API_KEY'] = 'test-admin-key'

def test_admin_endpoints():
    """Test admin endpoints with mocked dependencies"""
    print("🧪 Testing Admin API Endpoints...")
    
    try:
        # Mock all heavy dependencies
        with patch('api.main.whisper'), \
             patch('api.main.VideoProcessor'), \
             patch('api.main.process_video_job'), \
             patch('api.main.validate_video_files'):
            
            from fastapi.testclient import TestClient
            from api.main import app
            
            client = TestClient(app)
            
            # Mock services
            with patch('api.main.db_service') as mock_db, \
                 patch('api.main.credit_manager') as mock_credits, \
                 patch('api.main.AuthService') as mock_auth_class:
                
                # Test 1: Create user endpoint
                mock_db.create_user.return_value = "user-123"
                mock_credits.add_credits.return_value = True
                
                mock_auth_instance = Mock()
                mock_auth_instance.create_api_key.return_value = {
                    'api_key': 'vp_test_key',
                    'id': 'key-123'
                }
                mock_auth_class.return_value = mock_auth_instance
                
                response = client.post(
                    "/api/v1/admin/users",
                    data={
                        "email": "test@example.com",
                        "name": "Test User",
                        "subscription_tier": "premium",
                        "initial_credits": "50000",
                        "admin_api_key": "test-admin-key"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["user_id"] == "user-123"
                print("  ✅ Create user endpoint - PASSED")
                
                # Test 2: Provision credits endpoint
                mock_db.get_user.return_value = {"id": "user-123", "email": "test@example.com"}
                mock_credits.get_user_credits.return_value = {
                    "total_credits": 75000,
                    "remaining_credits": 75000
                }
                
                response = client.post(
                    "/api/v1/admin/users/user-123/credits",
                    data={
                        "credits_amount": "25000",
                        "description": "Monthly credits",
                        "admin_api_key": "test-admin-key"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["credits_added"] == 25000
                print("  ✅ Provision credits endpoint - PASSED")
                
                # Test 3: Get user details endpoint
                mock_auth_instance.list_user_api_keys.return_value = [
                    {
                        "id": "key-123",
                        "name": "Default API Key",
                        "key_prefix": "vp_test",
                        "is_active": True,
                        "created_at": "2025-01-08T10:30:00Z"
                    }
                ]
                
                response = client.get(
                    "/api/v1/admin/users/user-123?admin_api_key=test-admin-key"
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "user" in data
                assert "credits" in data
                assert "api_keys" in data
                print("  ✅ Get user details endpoint - PASSED")
                
                # Test 4: Cleanup endpoint
                with patch('api.main.storage_service') as mock_storage:
                    mock_storage.cleanup_temp_files.return_value = 5
                    
                    response = client.post(
                        "/admin/cleanup",
                        data={
                            "max_age_hours": "2",
                            "admin_api_key": "test-admin-key"
                        }
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["files_cleaned"] == 5
                    print("  ✅ Cleanup endpoint - PASSED")
                
                # Test 5: Invalid admin key
                response = client.post(
                    "/admin/cleanup",
                    data={
                        "max_age_hours": "2",
                        "admin_api_key": "invalid-key"
                    }
                )
                
                assert response.status_code == 403
                print("  ✅ Invalid admin key handling - PASSED")
        
        print("✅ Admin API Endpoints - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Admin API Endpoints - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_health_endpoints():
    """Test health and stats endpoints"""
    print("\n🧪 Testing Health & Stats Endpoints...")
    
    try:
        # Mock dependencies
        with patch('api.main.whisper'), \
             patch('api.main.VideoProcessor'), \
             patch('api.main.process_video_job'), \
             patch('api.main.validate_video_files'):
            
            from fastapi.testclient import TestClient
            from api.main import app
            
            client = TestClient(app)
            
            # Test 1: Root health check
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            print("  ✅ Root health check - PASSED")
            
            # Test 2: Detailed health check
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "services" in data
            print("  ✅ Detailed health check - PASSED")
            
            # Test 3: Stats endpoint (with auth)
            with patch('api.main.get_current_user') as mock_auth:
                mock_auth.return_value = {"user_id": "test-user"}
                
                with patch('api.main.storage_service') as mock_storage:
                    mock_storage.get_storage_stats.return_value = {
                        "temp_files_count": 5,
                        "temp_files_size": 1024000
                    }
                    
                    response = client.get(
                        "/stats",
                        headers={"Authorization": "Bearer test-token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert "total_jobs_processed" in data
                    print("  ✅ Stats endpoint - PASSED")
        
        print("✅ Health & Stats Endpoints - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Health & Stats Endpoints - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_storage_integration():
    """Test storage service integration with API"""
    print("\n🧪 Testing Storage Integration...")
    
    try:
        # Mock dependencies
        with patch('api.main.whisper'), \
             patch('api.main.VideoProcessor'), \
             patch('api.main.process_video_job'), \
             patch('api.main.validate_video_files'):
            
            # Import storage service used by API
            from api.main import storage_service
            
            # Test that storage service is hybrid storage
            from services.storage_hybrid import HybridStorageService
            assert isinstance(storage_service, HybridStorageService)
            print("  ✅ Hybrid storage integration - PASSED")
            
            # Test storage service methods
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch('services.storage_hybrid.settings') as mock_settings:
                    mock_settings.LOCAL_STORAGE_PATH = temp_dir
                    
                    # Test file operations
                    test_file = Path(temp_dir) / "test.mp4"
                    test_file.write_bytes(b"test content")
                    
                    # Test upload
                    result = storage_service.upload_to_storage(test_file, "temp/test.mp4")
                    assert result is not None
                    print("  ✅ Storage upload integration - PASSED")
                    
                    # Test cleanup
                    cleanup_count = storage_service.cleanup_temp_files(0)
                    assert cleanup_count >= 0
                    print("  ✅ Storage cleanup integration - PASSED")
                    
                    # Test stats
                    stats = storage_service.get_storage_stats()
                    assert isinstance(stats, dict)
                    print("  ✅ Storage stats integration - PASSED")
        
        print("✅ Storage Integration - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Storage Integration - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment_configuration():
    """Test environment configuration for deployment"""
    print("\n🧪 Testing Environment Configuration...")
    
    try:
        from config.settings import settings
        
        # Test admin API key
        assert hasattr(settings, 'ADMIN_API_KEY')
        assert settings.ADMIN_API_KEY is not None
        print("  ✅ Admin API key configuration - PASSED")
        
        # Test Azure storage configuration
        assert hasattr(settings, 'AZURE_STORAGE_CONNECTION_STRING')
        assert hasattr(settings, 'AZURE_STORAGE_ACCOUNT_NAME')
        assert hasattr(settings, 'AZURE_STORAGE_ACCOUNT_KEY')
        print("  ✅ Azure storage configuration - PASSED")
        
        # Test hybrid storage settings
        assert hasattr(settings, 'USE_LOCAL_STORAGE')
        assert hasattr(settings, 'LOCAL_STORAGE_PATH')
        assert hasattr(settings, 'TEMP_STORAGE_PATH')
        print("  ✅ Hybrid storage configuration - PASSED")
        
        # Test Supabase settings
        assert hasattr(settings, 'SUPABASE_URL')
        assert hasattr(settings, 'SUPABASE_SERVICE_KEY')
        print("  ✅ Supabase configuration - PASSED")
        
        print("✅ Environment Configuration - ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Environment Configuration - FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run focused API tests"""
    print("🚀 Running Focused API Tests for New Features")
    print("=" * 60)
    
    tests = [
        ("Admin API Endpoints", test_admin_endpoints),
        ("Health & Stats Endpoints", test_health_endpoints),
        ("Storage Integration", test_storage_integration),
        ("Environment Configuration", test_environment_configuration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FOCUSED API TEST RESULTS")
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
        print("\n🎉 ALL API TESTS PASSED! New features are ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the issues.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
