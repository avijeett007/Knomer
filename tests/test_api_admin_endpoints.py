"""
Tests for new admin API endpoints
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Set test environment
os.environ['USE_SQLITE'] = 'true'
os.environ['USE_LOCAL_STORAGE'] = 'true'
os.environ['ADMIN_API_KEY'] = 'test-admin-key'

# Import after setting environment
from api.main import app

class TestAdminEndpoints:
    """Test admin API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_service(self):
        """Mock database service"""
        with patch('api.main.db_service') as mock:
            yield mock
    
    @pytest.fixture
    def mock_credit_manager(self):
        """Mock credit manager"""
        with patch('api.main.credit_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_auth_service(self):
        """Mock auth service"""
        with patch('api.main.AuthService') as mock:
            yield mock
    
    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service"""
        with patch('api.main.storage_service') as mock:
            yield mock
    
    def test_create_user_with_credits_success(self, client, mock_db_service, mock_credit_manager, mock_auth_service):
        """Test successful user creation with credits"""
        # Setup mocks
        mock_db_service.create_user.return_value = "user-123"
        mock_credit_manager.add_credits.return_value = True
        
        mock_auth_instance = Mock()
        mock_auth_instance.create_api_key.return_value = {
            'api_key': 'vp_test_key_123',
            'id': 'key-123'
        }
        mock_auth_service.return_value = mock_auth_instance
        
        # Make request
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
        assert data["email"] == "test@example.com"
        assert data["subscription_tier"] == "premium"
        assert data["initial_credits"] == 50000
        assert data["api_key"] == "vp_test_key_123"
        
        # Verify calls
        mock_db_service.create_user.assert_called_once()
        mock_credit_manager.add_credits.assert_called_once_with(
            user_id="user-123",
            amount=50000,
            description="Initial credits for premium tier"
        )
    
    def test_create_user_invalid_admin_key(self, client):
        """Test user creation with invalid admin key"""
        response = client.post(
            "/api/v1/admin/users",
            data={
                "email": "test@example.com",
                "admin_api_key": "invalid-key"
            }
        )
        
        assert response.status_code == 403
        assert "Invalid admin API key" in response.json()["detail"]
    
    def test_create_user_db_failure(self, client, mock_db_service):
        """Test user creation when database fails"""
        mock_db_service.create_user.return_value = None
        
        response = client.post(
            "/api/v1/admin/users",
            data={
                "email": "test@example.com",
                "admin_api_key": "test-admin-key"
            }
        )
        
        assert response.status_code == 400
        assert "Failed to create user" in response.json()["detail"]
    
    def test_provision_monthly_credits_success(self, client, mock_db_service, mock_credit_manager):
        """Test successful credit provisioning"""
        # Setup mocks
        mock_db_service.get_user.return_value = {"id": "user-123", "email": "test@example.com"}
        mock_credit_manager.add_credits.return_value = True
        mock_credit_manager.get_user_credits.return_value = {
            "total_credits": 75000,
            "remaining_credits": 75000
        }
        
        response = client.post(
            "/api/v1/admin/users/user-123/credits",
            data={
                "credits_amount": "25000",
                "description": "Monthly premium credits",
                "admin_api_key": "test-admin-key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["user_id"] == "user-123"
        assert data["credits_added"] == 25000
        assert data["total_credits"] == 75000
        assert data["remaining_credits"] == 75000
        
        # Verify calls
        mock_credit_manager.add_credits.assert_called_once_with(
            user_id="user-123",
            amount=25000,
            description="Monthly premium credits"
        )
    
    def test_provision_credits_user_not_found(self, client, mock_db_service):
        """Test credit provisioning for non-existent user"""
        mock_db_service.get_user.return_value = None
        
        response = client.post(
            "/api/v1/admin/users/non-existent/credits",
            data={
                "credits_amount": "25000",
                "admin_api_key": "test-admin-key"
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_provision_credits_add_credits_failure(self, client, mock_db_service, mock_credit_manager):
        """Test credit provisioning when add_credits fails"""
        mock_db_service.get_user.return_value = {"id": "user-123"}
        mock_credit_manager.add_credits.return_value = False
        
        response = client.post(
            "/api/v1/admin/users/user-123/credits",
            data={
                "credits_amount": "25000",
                "admin_api_key": "test-admin-key"
            }
        )
        
        assert response.status_code == 400
        assert "Failed to add credits" in response.json()["detail"]
    
    def test_get_user_details_success(self, client, mock_db_service, mock_credit_manager, mock_auth_service):
        """Test successful user details retrieval"""
        # Setup mocks
        mock_db_service.get_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "subscription_tier": "premium",
            "is_active": True,
            "created_at": "2025-01-08T10:30:00Z"
        }
        
        mock_credit_manager.get_user_credits.return_value = {
            "total_credits": 50000,
            "used_credits": 5000,
            "remaining_credits": 45000,
            "last_updated": "2025-01-08T10:30:00Z"
        }
        
        mock_auth_instance = Mock()
        mock_auth_instance.list_user_api_keys.return_value = [
            {
                "id": "key-123",
                "name": "Default API Key",
                "key_prefix": "vp_test",
                "is_active": True,
                "created_at": "2025-01-08T10:30:00Z"
            }
        ]
        mock_auth_service.return_value = mock_auth_instance
        
        response = client.get(
            "/api/v1/admin/users/user-123?admin_api_key=test-admin-key"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user"]["id"] == "user-123"
        assert data["user"]["email"] == "test@example.com"
        assert data["credits"]["total_credits"] == 50000
        assert data["credits"]["remaining_credits"] == 45000
        assert data["api_keys_count"] == 1
        assert len(data["api_keys"]) == 1
    
    def test_get_user_details_user_not_found(self, client, mock_db_service):
        """Test user details for non-existent user"""
        mock_db_service.get_user.return_value = None
        
        response = client.get(
            "/api/v1/admin/users/non-existent?admin_api_key=test-admin-key"
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_cleanup_temp_files_success(self, client, mock_storage_service):
        """Test successful temp file cleanup"""
        mock_storage_service.cleanup_temp_files.return_value = 5
        
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
        assert data["max_age_hours"] == 2
        assert "Cleaned up 5 temporary files" in data["message"]
        
        mock_storage_service.cleanup_temp_files.assert_called_once_with(2)
    
    def test_cleanup_temp_files_no_cleanup_method(self, client, mock_storage_service):
        """Test cleanup when storage service doesn't have cleanup method"""
        # Remove cleanup_temp_files method from mock
        del mock_storage_service.cleanup_temp_files
        
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
        assert data["files_cleaned"] == 0
    
    def test_cleanup_invalid_admin_key(self, client):
        """Test cleanup with invalid admin key"""
        response = client.post(
            "/admin/cleanup",
            data={
                "max_age_hours": "2",
                "admin_api_key": "invalid-key"
            }
        )
        
        assert response.status_code == 403
        assert "Invalid admin API key" in response.json()["detail"]
    
    @patch('api.main.settings')
    def test_admin_key_from_settings(self, mock_settings, client, mock_storage_service):
        """Test that admin key is read from settings"""
        mock_settings.ADMIN_API_KEY = "settings-admin-key"
        mock_storage_service.cleanup_temp_files.return_value = 3
        
        response = client.post(
            "/admin/cleanup",
            data={
                "max_age_hours": "1",
                "admin_api_key": "settings-admin-key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_create_user_default_values(self, client, mock_db_service, mock_credit_manager, mock_auth_service):
        """Test user creation with default values"""
        mock_db_service.create_user.return_value = "user-456"
        mock_credit_manager.add_credits.return_value = True
        
        mock_auth_instance = Mock()
        mock_auth_instance.create_api_key.return_value = {
            'api_key': 'vp_default_key',
            'id': 'key-456'
        }
        mock_auth_service.return_value = mock_auth_instance
        
        response = client.post(
            "/api/v1/admin/users",
            data={
                "email": "default@example.com",
                "admin_api_key": "test-admin-key"
                # Using default values for name, subscription_tier, initial_credits
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["subscription_tier"] == "free"  # default
        assert data["initial_credits"] == 10000  # default
        
        # Verify user creation was called with defaults
        create_call_args = mock_db_service.create_user.call_args[0][0]
        assert create_call_args["subscription_tier"] == "free"
