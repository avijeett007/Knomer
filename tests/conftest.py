"""
Pytest configuration and fixtures for E2E tests
"""
import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient

# Import our application
from api.main import app
from services.database import DatabaseService
from services.storage import StorageService
from services.auth import AuthService
from services.credit_manager import CreditManager
from config.settings import settings

# Test configuration
TEST_API_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 300  # 5 minutes for video processing

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture(scope="session")
def test_data_dir():
    """Get the test data directory path."""
    return Path(__file__).parent / "sample_videos"

@pytest.fixture(scope="session")
def sample_videos(test_data_dir):
    """Get paths to sample video files."""
    return {
        "main_video": test_data_dir / "Yetti_Patel_s_London_Vlog.mp4",
        "intro_video": test_data_dir / "Yetti_Patel_s_UK_Tour_Intro.mp4",
        "transition_video": test_data_dir / "open_door_transition_first_clip.mp4",
        "animation_transition": test_data_dir / "Animation_Transition",
        "logo": test_data_dir / "knolabslogo.png"
    }

@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp(prefix="video_test_"))
    yield temp_path
    # Cleanup after tests
    if temp_path.exists():
        shutil.rmtree(temp_path)

@pytest.fixture(scope="function")
async def test_user():
    """Create a test user with API key."""
    auth_service = AuthService()
    
    # Create test user
    user_id = auth_service.create_user(
        email=f"test_{uuid4()}@example.com",
        name="Test User"
    )
    
    if not user_id:
        pytest.fail("Failed to create test user")
    
    # Create API key
    api_key_info = await auth_service.create_api_key(
        user_id=user_id,
        name="Test API Key"
    )
    
    if not api_key_info:
        pytest.fail("Failed to create API key")
    
    return {
        "user_id": user_id,
        "api_key": api_key_info["api_key"],
        "api_key_id": api_key_info["id"]
    }

@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Get authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {test_user['api_key']}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function")
def credit_manager():
    """Get credit manager instance."""
    return CreditManager()

@pytest.fixture(scope="function")
def storage_service():
    """Get storage service instance."""
    return StorageService()

@pytest.fixture(scope="function")
def db_service():
    """Get database service instance."""
    return DatabaseService()

@pytest.fixture(scope="function")
async def test_credits(test_user, credit_manager):
    """Add test credits to user account."""
    user_id = test_user["user_id"]
    
    # Add 1000 test credits
    success = credit_manager.add_credits(
        user_id=user_id,
        amount=1000,
        reason="Test credits"
    )
    
    if not success:
        pytest.fail("Failed to add test credits")
    
    return 1000

class VideoTestHelper:
    """Helper class for video testing operations."""
    
    @staticmethod
    def get_video_info(video_path: Path) -> Dict[str, Any]:
        """Get video information using ffprobe."""
        import subprocess
        import json
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def upload_test_video(storage_service: StorageService, video_path: Path, storage_path: str) -> str:
        """Upload a test video to storage and return URL."""
        return storage_service.upload_to_storage(video_path, storage_path)
    
    @staticmethod
    def validate_output_video(video_path: Path) -> bool:
        """Validate that output video is playable."""
        info = VideoTestHelper.get_video_info(video_path)
        return "error" not in info and "format" in info

@pytest.fixture(scope="function")
def video_helper():
    """Get video test helper instance."""
    return VideoTestHelper()

class APITestHelper:
    """Helper class for API testing operations."""
    
    def __init__(self, client: TestClient, auth_headers: Dict[str, str]):
        self.client = client
        self.auth_headers = auth_headers
    
    def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a video processing job."""
        response = self.client.post("/jobs", json=job_data, headers=self.auth_headers)
        return response.json(), response.status_code
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        response = self.client.get(f"/jobs/{job_id}", headers=self.auth_headers)
        return response.json(), response.status_code
    
    def wait_for_job_completion(self, job_id: str, timeout: int = TEST_TIMEOUT) -> Dict[str, Any]:
        """Wait for job to complete and return final status."""
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            job_data, status_code = self.get_job_status(job_id)
            
            if status_code != 200:
                return {"error": f"Failed to get job status: {status_code}"}
            
            job_status = job_data.get("job", {}).get("status")
            
            if job_status in ["completed", "failed", "cancelled"]:
                return job_data
            
            time.sleep(5)  # Wait 5 seconds before checking again
        
        return {"error": "Job timeout"}
    
    def estimate_credits(self, estimation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate credits for a job."""
        response = self.client.post("/credits/estimate", json=estimation_data, headers=self.auth_headers)
        return response.json(), response.status_code
    
    def get_user_credits(self) -> Dict[str, Any]:
        """Get user's current credits."""
        response = self.client.get("/credits", headers=self.auth_headers)
        return response.json(), response.status_code

@pytest.fixture(scope="function")
def api_helper(test_client, auth_headers):
    """Get API test helper instance."""
    return APITestHelper(test_client, auth_headers)

# Test data generators
def generate_simple_merge_job(video_urls: List[str]) -> Dict[str, Any]:
    """Generate a simple merge job configuration."""
    return {
        "job_type": "simple_merge",
        "videos": [
            {"url": url, "order_index": i}
            for i, url in enumerate(video_urls)
        ],
        "processing_options": {
            "platform": "youtube",
            "quality_preset": "balanced"
        }
    }

def generate_transition_merge_job(video_urls: List[str], transitions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a transition merge job configuration."""
    return {
        "job_type": "transition_merge",
        "videos": [
            {"url": url, "order_index": i}
            for i, url in enumerate(video_urls)
        ],
        "processing_options": {
            "platform": "youtube",
            "quality_preset": "balanced",
            "transitions": transitions
        }
    }

def generate_auto_effects_job(video_urls: List[str]) -> Dict[str, Any]:
    """Generate an auto effects job configuration."""
    return {
        "job_type": "auto_effects",
        "videos": [
            {"url": url, "order_index": i}
            for i, url in enumerate(video_urls)
        ],
        "processing_options": {
            "platform": "tiktok",
            "quality_preset": "balanced",
            "auto_effects": True,
            "enable_transcription": True,
            "ai_effects_based_on_transcript": True
        }
    }

def generate_logo_overlay_job(video_urls: List[str], logo_url: str) -> Dict[str, Any]:
    """Generate a logo overlay job configuration."""
    return {
        "job_type": "logo_overlay",
        "videos": [
            {"url": url, "order_index": i}
            for i, url in enumerate(video_urls)
        ],
        "processing_options": {
            "platform": "youtube",
            "quality_preset": "balanced",
            "logo_overlay": {
                "logo_url": logo_url,
                "position": "top-right",
                "size": 0.15,
                "opacity": 0.8
            }
        }
    }

# Export test data generators
pytest.generate_simple_merge_job = generate_simple_merge_job
pytest.generate_transition_merge_job = generate_transition_merge_job
pytest.generate_auto_effects_job = generate_auto_effects_job
pytest.generate_logo_overlay_job = generate_logo_overlay_job
