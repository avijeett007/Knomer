#!/usr/bin/env python3
"""
Local test runner - sets up SQLite database and runs E2E tests
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Setup local environment"""
    print("🔧 Setting up local environment...")
    
    # Use local environment file
    env_file = project_root / ".env.local"
    if env_file.exists():
        os.environ.update({
            line.split('=')[0]: line.split('=', 1)[1].strip('"')
            for line in env_file.read_text().splitlines()
            if '=' in line and not line.startswith('#')
        })
        print(f"✅ Loaded environment from {env_file}")
    
    # Create temp directories
    temp_dir = project_root / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    storage_dir = temp_dir / "storage"
    storage_dir.mkdir(exist_ok=True)
    
    print(f"✅ Created temp directories")

def setup_database():
    """Setup SQLite database with test data"""
    print("🗄️  Setting up SQLite database...")
    
    try:
        from database.sqlite_setup import setup_local_database
        test_data = setup_local_database()
        
        # Save test data for later use
        test_data_file = project_root / "test_data.json"
        import json
        with open(test_data_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"✅ Database setup complete")
        print(f"📧 Test user: {test_data['email']}")
        print(f"🔑 API Key: {test_data['api_key']}")
        
        return test_data
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return None

def check_redis():
    """Check if Redis is running"""
    print("🔍 Checking Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("💡 Start Redis with: redis-server")
        print("💡 Or use Docker: docker run -d -p 6379:6379 redis:alpine")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available"""
    print("🔍 Checking FFmpeg...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg is available")
        return True
    except Exception as e:
        print(f"⚠️  FFmpeg not available: {e}")
        print("💡 Install FFmpeg:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        return False

def start_api_server():
    """Start the API server"""
    print("🚀 Starting API server...")
    
    # Set environment for local mode
    env = os.environ.copy()
    env.update({
        'USE_SQLITE': 'true',
        'USE_LOCAL_STORAGE': 'true',
        'DEBUG': 'true'
    })
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn',
            'api.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload'
        ], env=env, cwd=str(project_root))
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if server is running
        import requests
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                print("✅ API server is running at http://localhost:8000")
                print("📚 API docs available at http://localhost:8000/docs")
                return process
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                process.terminate()
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Server not responding: {e}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def run_simple_api_test(test_data):
    """Run a simple API test"""
    print("🧪 Running simple API test...")
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get('http://localhost:8000/health')
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✅ Health check passed")
        
        # Test credits endpoint with API key
        headers = {'Authorization': f"Bearer {test_data['api_key']}"}
        response = requests.get('http://localhost:8000/credits', headers=headers)
        
        if response.status_code == 200:
            credits = response.json()
            print(f"✅ Credits check passed: {credits['remaining_credits']} credits available")
        else:
            print(f"⚠️  Credits check failed: {response.status_code} - {response.text}")
        
        # Test credit estimation
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
        
        response = requests.post(
            'http://localhost:8000/credits/estimate',
            json=estimation_data,
            headers=headers
        )
        
        if response.status_code == 200:
            estimate = response.json()
            print(f"✅ Credit estimation passed: {estimate['estimated_credits']} credits estimated")
        else:
            print(f"⚠️  Credit estimation failed: {response.status_code} - {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def run_video_processing_test(test_data):
    """Run a video processing test if test videos are available"""
    print("🎬 Checking for test videos...")
    
    test_videos_dir = project_root / "tests" / "sample_videos"
    required_videos = [
        "Yetti_Patel_s_London_Vlog.mp4",
        "Yetti_Patel_s_UK_Tour_Intro.mp4"
    ]
    
    available_videos = []
    for video in required_videos:
        video_path = test_videos_dir / video
        if video_path.exists():
            available_videos.append(video_path)
            print(f"✅ Found: {video}")
        else:
            print(f"⚠️  Missing: {video}")
    
    if len(available_videos) >= 2:
        print("🎬 Running video processing test...")
        
        try:
            import requests
            from services.storage_local import LocalStorageService
            
            # Upload test videos to local storage
            storage = LocalStorageService()
            video_urls = []
            
            for i, video_path in enumerate(available_videos[:2]):
                storage_path = f"test/video_{i}.mp4"
                url = storage.upload_to_storage(video_path, storage_path)
                if url:
                    video_urls.append(url)
                    print(f"✅ Uploaded: {video_path.name}")
            
            if len(video_urls) >= 2:
                # Create a simple merge job
                job_data = {
                    "job_type": "simple_merge",
                    "videos": [
                        {"url": video_urls[0], "order_index": 0},
                        {"url": video_urls[1], "order_index": 1}
                    ],
                    "processing_options": {
                        "platform": "youtube",
                        "quality_preset": "fast"
                    }
                }
                
                headers = {'Authorization': f"Bearer {test_data['api_key']}"}
                response = requests.post(
                    'http://localhost:8000/jobs',
                    json=job_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    job = response.json()
                    job_id = job['id']
                    print(f"✅ Job created: {job_id}")
                    print(f"📊 Status: {job['status']}")
                    print(f"💰 Estimated credits: {job.get('estimated_credits', 0)}")
                    
                    # Check job status
                    status_response = requests.get(
                        f'http://localhost:8000/jobs/{job_id}',
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"✅ Job status check passed: {status['job']['status']}")
                    
                    return True
                else:
                    print(f"❌ Job creation failed: {response.status_code} - {response.text}")
            
        except Exception as e:
            print(f"❌ Video processing test failed: {e}")
    
    else:
        print("⚠️  Not enough test videos for processing test")
        print("💡 Add test videos to tests/sample_videos/ directory")
    
    return False

def run_e2e_tests():
    """Run the E2E test suite"""
    print("🧪 Running E2E test suite...")
    
    try:
        # Set environment for tests
        env = os.environ.copy()
        env.update({
            'USE_SQLITE': 'true',
            'USE_LOCAL_STORAGE': 'true',
            'PYTHONPATH': str(project_root)
        })
        
        # Run specific E2E tests that work with local setup
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/test_api_endpoints.py',
            'tests/test_credit_system.py',
            '-v',
            '--tb=short',
            '--timeout=300'
        ]
        
        result = subprocess.run(cmd, env=env, cwd=str(project_root))
        
        if result.returncode == 0:
            print("✅ E2E tests passed!")
            return True
        else:
            print("❌ Some E2E tests failed")
            return False
            
    except Exception as e:
        print(f"❌ E2E test execution failed: {e}")
        return False

def main():
    """Main function"""
    print("🎯 Video Processing API - Local Test Runner")
    print("=" * 50)
    
    # Setup
    setup_environment()
    test_data = setup_database()
    
    if not test_data:
        print("❌ Database setup failed, exiting")
        sys.exit(1)
    
    # Check dependencies
    redis_ok = check_redis()
    ffmpeg_ok = check_ffmpeg()
    
    if not redis_ok:
        print("⚠️  Redis not available - some features may not work")
    
    if not ffmpeg_ok:
        print("⚠️  FFmpeg not available - video processing will fail")
    
    # Start API server
    server_process = start_api_server()
    
    if not server_process:
        print("❌ Failed to start API server, exiting")
        sys.exit(1)
    
    try:
        # Run tests
        print("\n" + "=" * 50)
        print("🧪 Running Tests")
        print("=" * 50)
        
        # Simple API test
        api_test_ok = run_simple_api_test(test_data)
        
        # Video processing test (if videos available)
        if ffmpeg_ok:
            video_test_ok = run_video_processing_test(test_data)
        else:
            video_test_ok = False
            print("⚠️  Skipping video processing test (FFmpeg not available)")
        
        # E2E tests
        e2e_test_ok = run_e2e_tests()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        print(f"API Tests: {'✅ PASSED' if api_test_ok else '❌ FAILED'}")
        print(f"Video Processing: {'✅ PASSED' if video_test_ok else '⚠️  SKIPPED/FAILED'}")
        print(f"E2E Tests: {'✅ PASSED' if e2e_test_ok else '❌ FAILED'}")
        
        if api_test_ok and e2e_test_ok:
            print("\n🎉 Local testing completed successfully!")
            print("🌐 API server is still running at http://localhost:8000")
            print("📚 API docs: http://localhost:8000/docs")
            print("🔑 Test API Key:", test_data['api_key'])
            print("\nPress Ctrl+C to stop the server")
            
            # Keep server running
            try:
                server_process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Stopping server...")
        else:
            print("\n💥 Some tests failed!")
            
    finally:
        # Cleanup
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        
        print("🧹 Cleanup complete")

if __name__ == "__main__":
    main()
