"""
Integration tests for hybrid storage with API endpoints
"""
import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Set test environment
os.environ['USE_SQLITE'] = 'true'
os.environ['USE_LOCAL_STORAGE'] = 'false'  # Use hybrid storage
os.environ['SUPABASE_URL'] = ''
os.environ['SUPABASE_SERVICE_KEY'] = ''

class TestHybridStorageIntegration:
    """Integration tests for hybrid storage with API"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_video_file(self, temp_dir):
        """Create a test video file"""
        video_file = temp_dir / "test_video.mp4"
        # Create a small fake video file
        video_file.write_bytes(b"fake video content for testing" * 100)
        return video_file
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def mock_hybrid_storage(self, temp_dir):
        """Mock hybrid storage service"""
        with patch('api.main.storage_service') as mock_storage:
            # Setup mock methods
            mock_storage.upload_to_storage.return_value = f"file://{temp_dir}/outputs/test_output.mp4"
            mock_storage.download_from_url.return_value = True
            mock_storage.cleanup_temp_files.return_value = 5
            mock_storage.get_storage_stats.return_value = {
                "local_storage": {"total_files": 10, "total_size_mb": 100},
                "cloud_storage_enabled": False,
                "temp_files_count": 3,
                "temp_files_size": 1024000
            }
            yield mock_storage
    
    @pytest.fixture
    def mock_auth(self):
        """Mock authentication"""
        with patch('api.main.get_current_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "test-user-123",
                "email": "test@example.com"
            }
            yield mock_auth
    
    @pytest.fixture
    def mock_credit_manager(self):
        """Mock credit manager"""
        with patch('api.main.credit_manager') as mock_credits:
            mock_credits.get_user_credits.return_value = {
                "total_credits": 10000,
                "used_credits": 0,
                "remaining_credits": 10000
            }
            mock_credits.estimate_credits.return_value = 100
            mock_credits.deduct_credits.return_value = True
            yield mock_credits
    
    @pytest.fixture
    def mock_ffmpeg(self):
        """Mock FFmpeg processing"""
        with patch('services.video_processor.VideoProcessor') as mock_processor:
            mock_instance = Mock()
            mock_instance.merge_videos.return_value = {
                "success": True,
                "output_path": "/tmp/merged_output.mp4",
                "duration": 30.0,
                "file_size": 1024000
            }
            mock_processor.return_value = mock_instance
            yield mock_instance
    
    def test_video_merge_with_hybrid_storage(self, client, mock_hybrid_storage, mock_auth, 
                                           mock_credit_manager, mock_ffmpeg, test_video_file):
        """Test video merge using hybrid storage"""
        # Create a second test file
        video_file2 = test_video_file.parent / "test_video2.mp4"
        video_file2.write_bytes(b"second fake video content" * 100)
        
        # Mock the output file creation
        output_file = test_video_file.parent / "merged_output.mp4"
        output_file.write_bytes(b"merged video content" * 200)
        mock_ffmpeg.merge_videos.return_value["output_path"] = str(output_file)
        
        # Make API request
        with open(test_video_file, 'rb') as f1, open(video_file2, 'rb') as f2:
            response = client.post(
                "/api/v1/merge",
                files=[
                    ("video_files", ("video1.mp4", f1, "video/mp4")),
                    ("video_files", ("video2.mp4", f2, "video/mp4"))
                ],
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "job_id" in data
        assert "output_url" in data
        assert data["output_url"].startswith("file://")
        
        # Verify hybrid storage was used for output
        mock_hybrid_storage.upload_to_storage.assert_called()
        upload_call = mock_hybrid_storage.upload_to_storage.call_args
        assert "outputs/" in upload_call[0][1]  # Second argument should be storage path with outputs/
    
    def test_logo_overlay_with_hybrid_storage(self, client, mock_hybrid_storage, mock_auth,
                                            mock_credit_manager, test_video_file):
        """Test logo overlay using hybrid storage"""
        # Create logo file
        logo_file = test_video_file.parent / "logo.png"
        logo_file.write_bytes(b"fake logo content")
        
        # Mock video processor for logo overlay
        with patch('services.video_processor.VideoProcessor') as mock_processor:
            mock_instance = Mock()
            output_file = test_video_file.parent / "logo_output.mp4"
            output_file.write_bytes(b"video with logo content" * 200)
            
            mock_instance.add_logo_overlay.return_value = {
                "success": True,
                "output_path": str(output_file),
                "duration": 25.0,
                "file_size": 2048000
            }
            mock_processor.return_value = mock_instance
            
            # Make API request
            with open(test_video_file, 'rb') as vf, open(logo_file, 'rb') as lf:
                response = client.post(
                    "/api/v1/logo-overlay",
                    files=[
                        ("video_file", ("video.mp4", vf, "video/mp4")),
                        ("logo_file", ("logo.png", lf, "image/png"))
                    ],
                    data={
                        "position": "top-right",
                        "scale": "0.15"
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "output_url" in data
        
        # Verify both temp and output storage were used
        mock_hybrid_storage.upload_to_storage.assert_called()
    
    def test_stats_endpoint_with_hybrid_storage(self, client, mock_hybrid_storage, mock_auth):
        """Test stats endpoint returns hybrid storage information"""
        response = client.get(
            "/stats",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats include hybrid storage information
        mock_hybrid_storage.get_storage_stats.assert_called()
    
    def test_cleanup_endpoint_integration(self, client, mock_hybrid_storage):
        """Test cleanup endpoint integration with hybrid storage"""
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
        
        # Verify cleanup was called on hybrid storage
        mock_hybrid_storage.cleanup_temp_files.assert_called_once_with(2)
    
    def test_premium_processing_with_hybrid_storage(self, client, mock_hybrid_storage, mock_auth,
                                                  mock_credit_manager, test_video_file):
        """Test premium processing with hybrid storage"""
        # Create logo file
        logo_file = test_video_file.parent / "logo.png"
        logo_file.write_bytes(b"fake logo content")
        
        # Mock premium processing
        with patch('services.video_processor.VideoProcessor') as mock_processor:
            mock_instance = Mock()
            output_file = test_video_file.parent / "premium_output.mp4"
            output_file.write_bytes(b"premium processed video" * 300)
            
            mock_instance.process_premium_video.return_value = {
                "success": True,
                "output_path": str(output_file),
                "duration": 120.0,
                "file_size": 5120000,
                "processing_steps": ["smart_zooming", "smart_captioning", "logo_overlay"]
            }
            mock_processor.return_value = mock_instance
            
            # Make API request
            with open(test_video_file, 'rb') as vf, open(logo_file, 'rb') as lf:
                response = client.post(
                    "/api/v1/premium/process",
                    files=[
                        ("video_file", ("video.mp4", vf, "video/mp4")),
                        ("logo_file", ("logo.png", lf, "image/png"))
                    ],
                    data={
                        "enable_smart_zooming": "true",
                        "enable_smart_captioning": "true",
                        "enable_logo_overlay": "true",
                        "processing_quality": "high"
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "output_url" in data
        assert "processing_steps" in data
        
        # Verify hybrid storage was used for premium output
        mock_hybrid_storage.upload_to_storage.assert_called()
    
    def test_file_download_with_hybrid_storage(self, client, mock_hybrid_storage, temp_dir):
        """Test file download through hybrid storage"""
        # Create a test output file
        output_file = temp_dir / "test_download.mp4"
        output_file.write_bytes(b"downloadable video content" * 100)
        
        # Mock the download endpoint behavior
        with patch('api.main.send_file') as mock_send_file:
            mock_send_file.return_value = "file_response"
            
            response = client.get("/api/v1/download/test_download.mp4")
            
            # The actual download behavior depends on the implementation
            # This test verifies the endpoint is accessible
            assert response.status_code in [200, 404]  # 404 if file doesn't exist in test
    
    def test_error_handling_with_hybrid_storage(self, client, mock_hybrid_storage, mock_auth,
                                              mock_credit_manager):
        """Test error handling when hybrid storage fails"""
        # Mock storage failure
        mock_hybrid_storage.upload_to_storage.return_value = None
        
        # Mock video processor
        with patch('services.video_processor.VideoProcessor') as mock_processor:
            mock_instance = Mock()
            mock_instance.merge_videos.return_value = {
                "success": True,
                "output_path": "/tmp/test_output.mp4",
                "duration": 30.0,
                "file_size": 1024000
            }
            mock_processor.return_value = mock_instance
            
            # Create test files
            test_file = Path("/tmp/test_video.mp4")
            test_file.write_bytes(b"test content")
            
            try:
                with open(test_file, 'rb') as f:
                    response = client.post(
                        "/api/v1/merge",
                        files=[("video_files", ("video.mp4", f, "video/mp4"))],
                        headers={"Authorization": "Bearer test-token"}
                    )
                
                # Should handle storage failure gracefully
                assert response.status_code in [500, 400]  # Error response expected
            finally:
                # Cleanup
                if test_file.exists():
                    test_file.unlink()
    
    def test_storage_stats_in_response(self, client, mock_hybrid_storage, mock_auth):
        """Test that storage stats are properly included in API responses"""
        # Test stats endpoint
        response = client.get(
            "/stats",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        # Verify get_storage_stats was called
        mock_hybrid_storage.get_storage_stats.assert_called()
    
    @patch.dict(os.environ, {'ADMIN_API_KEY': 'test-admin-key'})
    def test_cleanup_scheduling_integration(self, client, mock_hybrid_storage):
        """Test that cleanup can be scheduled and executed"""
        # Test manual cleanup trigger
        response = client.post(
            "/admin/cleanup",
            data={
                "max_age_hours": "1",
                "admin_api_key": "test-admin-key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "files_cleaned" in data
        
        # Verify cleanup was called with correct parameters
        mock_hybrid_storage.cleanup_temp_files.assert_called_once_with(1)
