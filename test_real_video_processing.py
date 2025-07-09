#!/usr/bin/env python3
"""
Test script for real video processing with actual video files.
This will show the actual FFmpeg operations and output files.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_GkqinmgNdpcPbLbFWz0yV-5k5T7cGLc1buZ2K66mRJU"  # From container logs

# Headers for authenticated requests
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_real_video_processing():
    """Test with real video files that exist"""
    print("🎬 Testing Real Video Processing")
    print("=" * 60)
    
    # Test with actual working video URLs
    job_data = {
        "job_type": "simple_merge",
        "videos": [
            {
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "duration": 10.0,
                "order_index": 0
            },
            {
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 
                "duration": 10.0,
                "order_index": 1
            }
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "transitions": [{"type": "fade", "duration": 1.0}]
        }
    }
    
    print("🔍 Creating job with real video files...")
    response = requests.post(f"{BASE_URL}/jobs", json=job_data, headers=HEADERS)
    
    if response.status_code == 200:
        job = response.json()
        job_id = job['id']
        print(f"✅ Job created successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {job['status']}")
        print(f"   Estimated Credits: {job['estimated_credits']}")
        
        # Monitor job progress
        print("\n🔍 Monitoring job progress...")
        for i in range(30):  # Wait up to 5 minutes
            time.sleep(10)
            status_response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
            if status_response.status_code == 200:
                status_data = status_response.json()
                job_status = status_data['job']['status']
                progress = status_data.get('progress_percentage', 'Unknown')
                
                print(f"   Attempt {i+1}: Status = {job_status}, Progress = {progress}%")
                
                if job_status in ['completed', 'failed', 'cancelled']:
                    print(f"\n🎯 Final Status: {job_status}")
                    if job_status == 'completed':
                        print("✅ Job completed successfully!")
                        # Get the final job details
                        final_response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
                        if final_response.status_code == 200:
                            final_data = final_response.json()
                            print(f"   Final job data: {json.dumps(final_data, indent=2)}")
                    else:
                        print(f"❌ Job failed or was cancelled")
                    break
            else:
                print(f"   Error checking status: {status_response.status_code}")
        else:
            print("⏰ Job monitoring timed out")
            
        return job_id
    else:
        print(f"❌ Failed to create job: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def check_worker_logs():
    """Check what the worker is doing"""
    print("\n🔍 Checking worker logs for FFmpeg operations...")
    import subprocess
    
    try:
        result = subprocess.run([
            "docker-compose", "-f", "docker-compose.local.yml", 
            "logs", "--tail", "50", "celery-worker"
        ], capture_output=True, text=True, cwd="/Users/avijitsarkar/Projects/Knotie-AI/video-merger-api")
        
        if result.returncode == 0:
            logs = result.stdout
            print("📋 Recent worker logs:")
            print("-" * 40)
            # Filter for interesting lines
            for line in logs.split('\n'):
                if any(keyword in line.lower() for keyword in ['ffmpeg', 'processing', 'error', 'completed', 'failed']):
                    print(line)
        else:
            print(f"❌ Error getting logs: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running docker command: {e}")

def check_output_files():
    """Check what output files are created"""
    print("\n🔍 Checking for output files...")
    import subprocess
    
    try:
        # Check if there are any output files in the container
        result = subprocess.run([
            "docker", "exec", "video-merger-api-celery-worker-1",
            "find", "/tmp", "-name", "*.mp4", "-o", "-name", "*.txt", "-o", "-name", "*.log"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            print("📁 Found output files:")
            for file in result.stdout.strip().split('\n'):
                if file.strip():
                    print(f"   {file}")
                    
                    # Try to get file info
                    info_result = subprocess.run([
                        "docker", "exec", "video-merger-api-celery-worker-1",
                        "ls", "-la", file
                    ], capture_output=True, text=True)
                    
                    if info_result.returncode == 0:
                        print(f"     {info_result.stdout.strip()}")
        else:
            print("📁 No output files found (they may have been cleaned up)")
            
    except Exception as e:
        print(f"❌ Error checking files: {e}")

if __name__ == "__main__":
    print("🎬 Real Video Processing Test")
    print("=" * 60)
    
    # Test real video processing
    job_id = test_real_video_processing()
    
    # Check logs and files
    check_worker_logs()
    check_output_files()
    
    print("\n" + "=" * 60)
    print("🎯 Real Video Processing Test Complete")
    
    if job_id:
        print(f"✅ Job {job_id} was created and processed")
        print("📋 Check the worker logs above for FFmpeg operations")
        print("📁 Check the output files section for generated files")
    else:
        print("❌ Job creation failed")
