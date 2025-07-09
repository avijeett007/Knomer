"""
Tests for hybrid storage service
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

# Set test environment before importing
os.environ['USE_SQLITE'] = 'true'
os.environ['USE_LOCAL_STORAGE'] = 'true'
os.environ['SUPABASE_URL'] = ''
os.environ['SUPABASE_SERVICE_KEY'] = ''

from services.storage_hybrid import HybridStorageService
from config.settings import settings

class TestHybridStorageService:
    """Test hybrid storage service functionality"""
    
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
    
    @pytest.fixture
    def hybrid_storage(self, temp_dir):
        """Create hybrid storage service with mocked settings"""
        with patch.object(settings, 'LOCAL_STORAGE_PATH', str(temp_dir)):
            storage = HybridStorageService()
            return storage
    
    def test_init_local_only(self, temp_dir):
        """Test initialization with local storage only"""
        with patch.object(settings, 'LOCAL_STORAGE_PATH', str(temp_dir)):
            with patch.object(settings, 'SUPABASE_URL', ''):
                storage = HybridStorageService()
                assert not storage.use_cloud_output
                assert storage.cloud_storage == storage.local_storage
    
    @patch('services.storage_hybrid.SupabaseStorageService')
    def test_init_with_supabase(self, mock_supabase, temp_dir):
        """Test initialization with Supabase storage"""
        with patch.object(settings, 'LOCAL_STORAGE_PATH', str(temp_dir)):
            with patch.object(settings, 'SUPABASE_URL', 'https://test.supabase.co'):
                with patch.object(settings, 'SUPABASE_SERVICE_KEY', 'test-key'):
                    with patch('services.storage_hybrid.SUPABASE_AVAILABLE', True):
                        storage = HybridStorageService()
                        assert storage.use_cloud_output
                        mock_supabase.assert_called_once()
    
    def test_upload_temp_file(self, hybrid_storage, test_file, temp_dir):
        """Test uploading temporary file"""
        result = hybrid_storage.upload_temp_file(test_file, "test_temp.mp4")
        
        assert result is not None
        assert result.startswith("file://")
        
        # Check file was copied to temp directory
        temp_path = temp_dir / "temp" / "test_temp.mp4"
        assert temp_path.exists()
        assert temp_path.read_bytes() == test_file.read_bytes()
    
    def test_upload_output_file_local(self, hybrid_storage, test_file, temp_dir):
        """Test uploading output file to local storage"""
        result = hybrid_storage.upload_output_file(test_file, "test_output.mp4")
        
        assert result is not None
        assert result.startswith("file://")
        
        # Check file was copied to outputs directory
        output_path = temp_dir / "outputs" / "test_output.mp4"
        assert output_path.exists()
        assert output_path.read_bytes() == test_file.read_bytes()
    
    @patch('services.storage_hybrid.SupabaseStorageService')
    def test_upload_output_file_cloud(self, mock_supabase_class, test_file, temp_dir):
        """Test uploading output file to cloud storage"""
        # Setup mock
        mock_supabase = Mock()
        mock_supabase.upload_to_storage.return_value = "https://supabase.co/test_output.mp4"
        mock_supabase_class.return_value = mock_supabase
        
        with patch.object(settings, 'LOCAL_STORAGE_PATH', str(temp_dir)):
            with patch.object(settings, 'SUPABASE_URL', 'https://test.supabase.co'):
                with patch.object(settings, 'SUPABASE_SERVICE_KEY', 'test-key'):
                    with patch('services.storage_hybrid.SUPABASE_AVAILABLE', True):
                        storage = HybridStorageService()
                        
                        result = storage.upload_output_file(test_file, "test_output.mp4")
                        
                        assert result == "https://supabase.co/test_output.mp4"
                        mock_supabase.upload_to_storage.assert_called_once_with(
                            test_file, "outputs/test_output.mp4"
                        )
    
    def test_upload_to_storage_routing(self, hybrid_storage, test_file):
        """Test that upload_to_storage routes correctly based on path"""
        # Test temp file routing
        with patch.object(hybrid_storage, 'upload_temp_file') as mock_temp:
            mock_temp.return_value = "temp_result"
            result = hybrid_storage.upload_to_storage(test_file, "temp/test.mp4")
            assert result == "temp_result"
            mock_temp.assert_called_once_with(test_file, "temp/test.mp4")
        
        # Test processing file routing
        with patch.object(hybrid_storage, 'upload_temp_file') as mock_temp:
            mock_temp.return_value = "processing_result"
            result = hybrid_storage.upload_to_storage(test_file, "processing/test.mp4")
            assert result == "processing_result"
            mock_temp.assert_called_once_with(test_file, "processing/test.mp4")
        
        # Test output file routing
        with patch.object(hybrid_storage, 'upload_output_file') as mock_output:
            mock_output.return_value = "output_result"
            result = hybrid_storage.upload_to_storage(test_file, "outputs/test.mp4")
            assert result == "output_result"
            mock_output.assert_called_once_with(test_file, "outputs/test.mp4")
    
    def test_download_from_storage(self, hybrid_storage, temp_dir):
        """Test downloading from storage"""
        # Create a source file
        source_file = temp_dir / "temp" / "source.mp4"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_bytes(b"test content")
        
        # Download to different location
        dest_file = temp_dir / "downloaded.mp4"
        result = hybrid_storage.download_from_storage("temp/source.mp4", dest_file)
        
        assert result is True
        assert dest_file.exists()
        assert dest_file.read_bytes() == b"test content"
    
    @patch('requests.get')
    def test_download_from_url_http(self, mock_get, hybrid_storage, temp_dir):
        """Test downloading from HTTP URL"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_response
        
        dest_file = temp_dir / "downloaded.mp4"
        result = hybrid_storage.download_from_url("https://example.com/video.mp4", dest_file)
        
        assert result is True
        assert dest_file.exists()
        assert dest_file.read_bytes() == b"chunk1chunk2"
    
    def test_download_from_url_file(self, hybrid_storage, test_file, temp_dir):
        """Test downloading from file:// URL"""
        dest_file = temp_dir / "downloaded.mp4"
        file_url = f"file://{test_file.absolute()}"
        
        result = hybrid_storage.download_from_url(file_url, dest_file)
        
        assert result is True
        assert dest_file.exists()
        assert dest_file.read_bytes() == test_file.read_bytes()
    
    def test_cleanup_temp_files(self, hybrid_storage, temp_dir):
        """Test cleanup of temporary files"""
        import time
        
        # Create temp directory and files
        temp_dir_path = temp_dir / "temp"
        temp_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create old file (simulate by setting modification time)
        old_file = temp_dir_path / "old_file.mp4"
        old_file.write_bytes(b"old content")
        
        # Create new file
        new_file = temp_dir_path / "new_file.mp4"
        new_file.write_bytes(b"new content")
        
        # Modify old file timestamp to be older than 2 hours
        old_time = time.time() - (3 * 3600)  # 3 hours ago
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup
        cleaned_count = hybrid_storage.cleanup_temp_files(max_age_hours=2)
        
        assert cleaned_count == 1
        assert not old_file.exists()
        assert new_file.exists()
    
    def test_get_storage_stats(self, hybrid_storage, temp_dir):
        """Test getting storage statistics"""
        # Create some temp files
        temp_dir_path = temp_dir / "temp"
        temp_dir_path.mkdir(parents=True, exist_ok=True)
        
        file1 = temp_dir_path / "file1.mp4"
        file1.write_bytes(b"content1")
        
        file2 = temp_dir_path / "file2.mp4"
        file2.write_bytes(b"content2")
        
        stats = hybrid_storage.get_storage_stats()
        
        assert "local_storage" in stats
        assert "cloud_storage_enabled" in stats
        assert "temp_files_count" in stats
        assert "temp_files_size" in stats
        assert stats["cloud_storage_enabled"] is False
        assert stats["temp_files_count"] == 2
    
    def test_delete_file(self, hybrid_storage, temp_dir):
        """Test deleting files"""
        # Create a test file
        test_file = temp_dir / "outputs" / "test_delete.mp4"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"delete me")
        
        # Delete the file
        result = hybrid_storage.delete_file("outputs/test_delete.mp4")
        
        assert result is not None
        assert result > 0  # Should return file size
    
    def test_create_signed_url(self, hybrid_storage, temp_dir):
        """Test creating signed URLs"""
        # Create a test file
        test_file = temp_dir / "outputs" / "test_signed.mp4"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"signed content")
        
        # Create signed URL
        signed_url = hybrid_storage.create_signed_url("outputs/test_signed.mp4")
        
        assert signed_url is not None
        assert signed_url.startswith("file://")
    
    def test_error_handling(self, hybrid_storage):
        """Test error handling for various operations"""
        # Test upload with non-existent file
        non_existent = Path("/non/existent/file.mp4")
        result = hybrid_storage.upload_temp_file(non_existent, "test.mp4")
        assert result is None
        
        # Test download to invalid path
        result = hybrid_storage.download_from_storage("non/existent.mp4", Path("/invalid/path.mp4"))
        assert result is False
        
        # Test cleanup with invalid directory
        with patch.object(settings, 'LOCAL_STORAGE_PATH', '/invalid/path'):
            cleaned_count = hybrid_storage.cleanup_temp_files()
            assert cleaned_count == 0
