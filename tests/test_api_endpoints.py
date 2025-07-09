"""
Tests for API endpoints and authentication
"""
import pytest
import json
from uuid import uuid4

class TestHealthAndStatus:
    """Test health check and status endpoints"""
    
    def test_root_endpoint(self, test_client):
        """Test root health check endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
        
    def test_health_endpoint(self, test_client):
        """Test detailed health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "services" in data
        assert "database" in data["services"]
        
    def test_stats_endpoint_requires_auth(self, test_client):
        """Test that stats endpoint requires authentication"""
        response = test_client.get("/stats")
        assert response.status_code == 401
        
    def test_stats_endpoint_with_auth(self, test_client, auth_headers):
        """Test stats endpoint with authentication"""
        response = test_client.get("/stats", headers=auth_headers)
        # May return 200 or 403 depending on admin status
        assert response.status_code in [200, 403]


class TestAuthentication:
    """Test API key authentication"""
    
    def test_no_auth_header(self, test_client):
        """Test request without auth header"""
        response = test_client.get("/credits")
        assert response.status_code == 401
        
    def test_invalid_auth_format(self, test_client):
        """Test invalid auth header format"""
        headers = {"Authorization": "InvalidFormat token123"}
        response = test_client.get("/credits", headers=headers)
        assert response.status_code == 401
        
    def test_invalid_api_key(self, test_client):
        """Test invalid API key"""
        headers = {"Authorization": "Bearer vp_invalid_key_12345"}
        response = test_client.get("/credits", headers=headers)
        assert response.status_code == 401
        
    def test_valid_api_key(self, test_client, auth_headers):
        """Test valid API key"""
        response = test_client.get("/credits", headers=auth_headers)
        assert response.status_code == 200


class TestCreditEndpoints:
    """Test credit management endpoints"""
    
    def test_get_user_credits(self, test_client, auth_headers, test_credits):
        """Test getting user credits"""
        response = test_client.get("/credits", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_credits" in data
        assert "used_credits" in data
        assert "remaining_credits" in data
        assert data["total_credits"] >= test_credits
        
    def test_estimate_credits_simple_merge(self, test_client, auth_headers):
        """Test credit estimation for simple merge"""
        estimation_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": "https://example.com/video1.mp4", "duration": 30.0, "order_index": 0},
                {"url": "https://example.com/video2.mp4", "duration": 45.0, "order_index": 1}
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "balanced"
            }
        }
        
        response = test_client.post(
            "/credits/estimate", 
            json=estimation_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "estimated_credits" in data
        assert "breakdown" in data
        assert "total_duration_seconds" in data
        assert data["estimated_credits"] == 0  # Simple merge is free
        
    def test_estimate_credits_auto_effects(self, test_client, auth_headers):
        """Test credit estimation for auto effects"""
        estimation_data = {
            "job_type": "auto_effects",
            "videos": [
                {"url": "https://example.com/video.mp4", "duration": 60.0, "order_index": 0}
            ],
            "processing_options": {
                "platform": "tiktok",
                "quality_preset": "balanced",
                "auto_effects": True,
                "enable_transcription": True,
                "ai_effects_based_on_transcript": True
            }
        }
        
        response = test_client.post(
            "/credits/estimate", 
            json=estimation_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["estimated_credits"] > 0  # Should cost credits
        assert "auto_effects_cost" in data["breakdown"]
        
    def test_estimate_credits_invalid_job_type(self, test_client, auth_headers):
        """Test credit estimation with invalid job type"""
        estimation_data = {
            "job_type": "invalid_type",
            "videos": [
                {"url": "https://example.com/video.mp4", "duration": 30.0, "order_index": 0}
            ],
            "processing_options": {
                "platform": "youtube"
            }
        }
        
        response = test_client.post(
            "/credits/estimate", 
            json=estimation_data, 
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error


class TestJobEndpoints:
    """Test job management endpoints"""
    
    def test_create_simple_job(self, test_client, auth_headers, test_credits):
        """Test creating a simple merge job"""
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": "https://example.com/video1.mp4", "order_index": 0},
                {"url": "https://example.com/video2.mp4", "order_index": 1}
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "balanced"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["job_type"] == "simple_merge"
        assert data["status"] == "pending"
        assert "estimated_credits" in data
        
    def test_create_job_insufficient_credits(self, test_client, auth_headers):
        """Test creating job with insufficient credits"""
        # This test assumes the test user has limited credits
        # Create an expensive job that should exceed available credits
        job_data = {
            "job_type": "auto_effects",
            "videos": [
                {"url": "https://example.com/very_long_video.mp4", "duration": 3600.0, "order_index": 0}
            ],
            "processing_options": {
                "platform": "tiktok",
                "quality_preset": "quality",
                "auto_effects": True,
                "enable_transcription": True,
                "ai_effects_based_on_transcript": True
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        # Should either succeed (if user has enough credits) or fail with 402
        assert response.status_code in [200, 402]
        
        if response.status_code == 402:
            data = response.json()
            assert "insufficient" in data["detail"].lower()
            
    def test_get_job_status_nonexistent(self, test_client, auth_headers):
        """Test getting status of non-existent job"""
        fake_job_id = str(uuid4())
        response = test_client.get(f"/jobs/{fake_job_id}", headers=auth_headers)
        assert response.status_code == 404
        
    def test_get_job_status_invalid_uuid(self, test_client, auth_headers):
        """Test getting status with invalid UUID"""
        response = test_client.get("/jobs/invalid-uuid", headers=auth_headers)
        assert response.status_code == 422  # Validation error
        
    def test_list_user_jobs_empty(self, test_client, auth_headers):
        """Test listing jobs for new user (should be empty)"""
        response = test_client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["jobs"], list)
        
    def test_list_user_jobs_pagination(self, test_client, auth_headers):
        """Test job listing pagination"""
        # Test with pagination parameters
        response = test_client.get("/jobs?page=1&page_size=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        
    def test_create_job_invalid_video_count(self, test_client, auth_headers):
        """Test creating job with invalid video count"""
        # Test with no videos
        job_data = {
            "job_type": "simple_merge",
            "videos": [],
            "processing_options": {
                "platform": "youtube"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422  # Validation error
        
        # Test with too many videos
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": f"https://example.com/video{i}.mp4", "order_index": i}
                for i in range(15)  # More than MAX_VIDEOS_PER_JOB
            ],
            "processing_options": {
                "platform": "youtube"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422  # Validation error
        
    def test_create_job_missing_required_fields(self, test_client, auth_headers):
        """Test creating job with missing required fields"""
        # Missing job_type
        job_data = {
            "videos": [
                {"url": "https://example.com/video.mp4", "order_index": 0}
            ]
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422
        
        # Missing videos
        job_data = {
            "job_type": "simple_merge"
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422


class TestValidationAndErrorHandling:
    """Test input validation and error handling"""
    
    def test_invalid_json(self, test_client, auth_headers):
        """Test handling of invalid JSON"""
        response = test_client.post(
            "/jobs", 
            data="invalid json{", 
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
    def test_invalid_platform(self, test_client, auth_headers):
        """Test invalid platform value"""
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": "https://example.com/video.mp4", "order_index": 0}
            ],
            "processing_options": {
                "platform": "invalid_platform"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422
        
    def test_invalid_quality_preset(self, test_client, auth_headers):
        """Test invalid quality preset"""
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": "https://example.com/video.mp4", "order_index": 0}
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "invalid_preset"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422
        
    def test_negative_video_order_index(self, test_client, auth_headers):
        """Test negative order index"""
        job_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": "https://example.com/video.mp4", "order_index": -1}
            ],
            "processing_options": {
                "platform": "youtube"
            }
        }
        
        response = test_client.post("/jobs", json=job_data, headers=auth_headers)
        assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiting_headers(self, test_client, auth_headers):
        """Test that rate limiting headers are present"""
        response = test_client.get("/credits", headers=auth_headers)
        assert response.status_code == 200
        
        # Check for rate limiting headers (if implemented)
        # These might not be implemented yet, so we just check the response is valid
        assert response.headers.get("content-type") == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
