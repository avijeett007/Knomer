"""
Tests for Azure Blob Storage service
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

# Set test environment
os.environ['USE_SQLITE'] = 'true'
os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net'

class TestAzureStorageService:
    """Test Azure Blob Storage service functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file"""
        test_file = temp_dir / "test_video.mp4"
        test_file.write_bytes(b"fake video content for testing")
        return test_file
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_init_success(self, mock_blob_client):
        """Test successful initialization"""
        from services.storage_azure import AzureStorageService
        
        # Mock the blob service client
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        # Mock container client
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        storage = AzureStorageService()
        
        assert storage.blob_service == mock_client
        assert storage.container_name == "video-processing"
        mock_blob_client.from_connection_string.assert_called_once()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', False)
    def test_init_azure_not_available(self):
        """Test initialization when Azure SDK is not available"""
        from services.storage_azure import AzureStorageService
        
        with pytest.raises(ImportError, match="Azure Storage SDK not installed"):
            AzureStorageService()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_init_no_connection_string(self, mock_blob_client):
        """Test initialization without connection string"""
        from services.storage_azure import AzureStorageService
        
        with patch('services.storage_azure.settings.AZURE_STORAGE_CONNECTION_STRING', ''):
            with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING not configured"):
                AzureStorageService()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_ensure_container_exists(self, mock_blob_client):
        """Test container creation when it doesn't exist"""
        from services.storage_azure import AzureStorageService
        from azure.core.exceptions import ResourceNotFoundError
        
        # Mock the blob service client
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        # Mock container client that raises ResourceNotFoundError first
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.side_effect = ResourceNotFoundError("Container not found")
        
        storage = AzureStorageService()
        
        # Verify create_container was called
        mock_client.create_container.assert_called_once_with(
            "video-processing",
            public_access='blob'
        )
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_upload_to_storage_success(self, mock_blob_client, test_file):
        """Test successful file upload"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        mock_blob_client_instance = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client_instance
        mock_blob_client_instance.url = "https://test.blob.core.windows.net/video-processing/test.mp4"
        
        storage = AzureStorageService()
        result = storage.upload_to_storage(test_file, "test.mp4")
        
        assert result == "https://test.blob.core.windows.net/video-processing/test.mp4"
        mock_blob_client_instance.upload_blob.assert_called_once()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_upload_to_storage_file_not_found(self, mock_blob_client):
        """Test upload with non-existent file"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        storage = AzureStorageService()
        non_existent_file = Path("/non/existent/file.mp4")
        result = storage.upload_to_storage(non_existent_file, "test.mp4")
        
        assert result is None
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_download_from_storage_success(self, mock_blob_client, temp_dir):
        """Test successful file download"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        mock_blob_client_instance = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client_instance
        
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"downloaded content"
        mock_blob_client_instance.download_blob.return_value = mock_download_stream
        
        storage = AzureStorageService()
        local_path = temp_dir / "downloaded.mp4"
        result = storage.download_from_storage("test.mp4", local_path)
        
        assert result is True
        assert local_path.exists()
        assert local_path.read_bytes() == b"downloaded content"
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    @patch('requests.get')
    def test_download_from_url_azure_blob(self, mock_get, mock_blob_client, temp_dir):
        """Test downloading from Azure blob URL"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        mock_blob_client_instance = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client_instance
        
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"azure blob content"
        mock_blob_client_instance.download_blob.return_value = mock_download_stream
        
        storage = AzureStorageService()
        local_path = temp_dir / "downloaded.mp4"
        azure_url = "https://test.blob.core.windows.net/container/blob.mp4"
        
        result = storage.download_from_url(azure_url, local_path)
        
        assert result is True
        assert local_path.exists()
        assert local_path.read_bytes() == b"azure blob content"
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    @patch('requests.get')
    def test_download_from_url_http(self, mock_get, mock_blob_client, temp_dir):
        """Test downloading from regular HTTP URL"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_response
        
        storage = AzureStorageService()
        local_path = temp_dir / "downloaded.mp4"
        
        result = storage.download_from_url("https://example.com/video.mp4", local_path)
        
        assert result is True
        assert local_path.exists()
        assert local_path.read_bytes() == b"chunk1chunk2"
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_delete_file_success(self, mock_blob_client):
        """Test successful file deletion"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        mock_blob_client_instance = Mock()
        mock_client.get_blob_client.return_value = mock_blob_client_instance
        
        # Mock blob properties
        mock_properties = Mock()
        mock_properties.size = 1024
        mock_blob_client_instance.get_blob_properties.return_value = mock_properties
        
        storage = AzureStorageService()
        result = storage.delete_file("test.mp4")
        
        assert result == 1024
        mock_blob_client_instance.delete_blob.assert_called_once()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_get_content_type(self, mock_blob_client):
        """Test content type detection"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        storage = AzureStorageService()
        
        # Test various file types
        assert storage._get_content_type(Path("test.mp4")) == "video/mp4"
        assert storage._get_content_type(Path("test.mov")) == "video/quicktime"
        assert storage._get_content_type(Path("test.png")) == "image/png"
        assert storage._get_content_type(Path("test.unknown")) == "application/octet-stream"
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    @patch('services.storage_azure.generate_blob_sas')
    def test_create_signed_url(self, mock_generate_sas, mock_blob_client):
        """Test creating signed URLs"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_client.account_name = "testaccount"
        mock_client.credential.account_key = "testkey"
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        mock_blob_client_instance = Mock()
        mock_blob_client_instance.url = "https://test.blob.core.windows.net/container/test.mp4"
        mock_client.get_blob_client.return_value = mock_blob_client_instance
        
        mock_generate_sas.return_value = "sas_token_here"
        
        storage = AzureStorageService()
        result = storage.create_signed_url("test.mp4", 3600)
        
        assert result == "https://test.blob.core.windows.net/container/test.mp4?sas_token_here"
        mock_generate_sas.assert_called_once()
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_list_files(self, mock_blob_client):
        """Test listing files in container"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        # Mock blob list
        mock_blob1 = Mock()
        mock_blob1.name = "file1.mp4"
        mock_blob2 = Mock()
        mock_blob2.name = "file2.mp4"
        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]
        
        storage = AzureStorageService()
        result = storage.list_files()
        
        assert result == ["file1.mp4", "file2.mp4"]
        mock_container_client.list_blobs.assert_called_once_with(name_starts_with="")
    
    @patch('services.storage_azure.AZURE_AVAILABLE', True)
    @patch('services.storage_azure.BlobServiceClient')
    def test_extract_storage_path(self, mock_blob_client):
        """Test extracting storage path from URL"""
        from services.storage_azure import AzureStorageService
        
        # Setup mocks
        mock_client = Mock()
        mock_blob_client.from_connection_string.return_value = mock_client
        
        mock_container_client = Mock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_container_properties.return_value = {"name": "test"}
        
        storage = AzureStorageService()
        
        # Test URL extraction
        url = "https://test.blob.core.windows.net/container/path/to/file.mp4"
        result = storage._extract_storage_path(url)
        assert result == "path/to/file.mp4"
        
        # Test plain path
        result = storage._extract_storage_path("path/to/file.mp4")
        assert result == "path/to/file.mp4"
