#!/usr/bin/env python3
"""
Test script using the actual sample videos from tests/sample_videos/
This will show real FFmpeg operations and keep output files for inspection.
"""

import requests
import json
import time
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_UHUnroUYlsyEg8TD79ef4ApKarClmF9FXYH6ROSfM3g"  # From container logs

# Headers for authenticated requests
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def upload_sample_videos_to_container():
    """Upload sample videos to the container for processing"""
    print("📁 Uploading sample videos to container...")
    
    sample_videos_dir = Path("tests/sample_videos")
    videos = [
        "Yetti_Patel_s_London_Vlog.mp4",
        "Yetti_Patel_s_UK_Tour_Intro.mp4",
        "open_door_transition_first_clip.mp4"
    ]
    
    uploaded_paths = {}
    
    for video in videos:
        local_path = sample_videos_dir / video
        if local_path.exists():
            # Copy video to container's temp directory
            container_path = f"/tmp/video_processing/{video}"
            try:
                result = subprocess.run([
                    "docker", "cp", str(local_path), 
                    f"video-merger-api-celery-worker-1:{container_path}"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    uploaded_paths[video] = f"file://{container_path}"
                    print(f"✅ Uploaded: {video}")
                else:
                    print(f"❌ Failed to upload {video}: {result.stderr}")
            except Exception as e:
                print(f"❌ Error uploading {video}: {e}")
        else:
            print(f"⚠️  Video not found: {local_path}")
    
    return uploaded_paths

def test_simple_merge_with_sample_videos():
    """Test simple merge using sample videos"""
    print("\n🎬 Testing Simple Merge with Sample Videos")
    print("=" * 60)
    
    # Upload videos first
    uploaded_videos = upload_sample_videos_to_container()
    
    if len(uploaded_videos) < 2:
        print("❌ Need at least 2 videos for merge test")
        return None
    
    # Use the first two videos
    video_list = list(uploaded_videos.items())
    
    job_data = {
        "job_type": "simple_merge",
        "videos": [
            {
                "url": video_list[0][1],  # First video URL
                "duration": 30.0,
                "order_index": 0
            },
            {
                "url": video_list[1][1],  # Second video URL
                "duration": 30.0,
                "order_index": 1
            }
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "transitions": [{"type": "fade", "duration": 1.0}]
        }
    }
    
    print(f"🔍 Creating merge job with videos:")
    print(f"   Video 1: {video_list[0][0]}")
    print(f"   Video 2: {video_list[1][0]}")
    
    response = requests.post(f"{BASE_URL}/jobs", json=job_data, headers=HEADERS)
    
    if response.status_code == 200:
        job = response.json()
        job_id = job['id']
        print(f"✅ Job created successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {job['status']}")
        print(f"   Estimated Credits: {job['estimated_credits']}")
        
        return job_id
    else:
        print(f"❌ Failed to create job: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_auto_effects_with_sample_video():
    """Test auto-effects with a sample video"""
    print("\n🎬 Testing Auto-Effects with Sample Video")
    print("=" * 60)
    
    # Upload videos first
    uploaded_videos = upload_sample_videos_to_container()
    
    if not uploaded_videos:
        print("❌ No videos available for auto-effects test")
        return None
    
    # Use the first video
    video_item = list(uploaded_videos.items())[0]
    
    job_data = {
        "job_type": "auto_effects",
        "videos": [
            {
                "url": video_item[1],
                "duration": 60.0,
                "order_index": 0
            }
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "enable_transcription": True,
            "auto_effects": True,
            "ai_effects_based_on_transcript": True
        }
    }
    
    print(f"🔍 Creating auto-effects job with video: {video_item[0]}")
    
    response = requests.post(f"{BASE_URL}/jobs", json=job_data, headers=HEADERS)
    
    if response.status_code == 200:
        job = response.json()
        job_id = job['id']
        print(f"✅ Auto-effects job created!")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {job['status']}")
        print(f"   Estimated Credits: {job['estimated_credits']}")
        
        return job_id
    else:
        print(f"❌ Failed to create auto-effects job: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def monitor_job_progress(job_id, max_wait_minutes=10):
    """Monitor job progress and show detailed logs"""
    print(f"\n🔍 Monitoring job {job_id}...")
    
    for i in range(max_wait_minutes * 6):  # Check every 10 seconds
        time.sleep(10)
        
        # Check job status
        status_response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
        if status_response.status_code == 200:
            status_data = status_response.json()
            job_status = status_data['job']['status']
            progress = status_data.get('progress_percentage', 'Unknown')
            
            print(f"   Check {i+1}: Status = {job_status}, Progress = {progress}%")
            
            if job_status in ['completed', 'failed', 'cancelled']:
                print(f"\n🎯 Final Status: {job_status}")
                return job_status
        else:
            print(f"   Error checking status: {status_response.status_code}")
    
    print("⏰ Job monitoring timed out")
    return "timeout"

def check_ffmpeg_logs():
    """Check worker logs for FFmpeg operations"""
    print("\n🔍 Checking FFmpeg Operations in Worker Logs...")
    print("=" * 60)
    
    try:
        result = subprocess.run([
            "docker-compose", "-f", "docker-compose.local.yml", 
            "logs", "--tail", "100", "celery-worker"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            logs = result.stdout
            print("📋 FFmpeg and Processing Logs:")
            print("-" * 40)
            
            # Filter for interesting lines
            for line in logs.split('\n'):
                if any(keyword in line.lower() for keyword in [
                    'ffmpeg', 'processing', 'concat', 'video', 'audio', 
                    'duration', 'fps', 'bitrate', 'resolution', 'codec'
                ]):
                    print(line)
        else:
            print(f"❌ Error getting logs: {result.stderr}")
    except Exception as e:
        print(f"❌ Error running docker command: {e}")

def check_output_files():
    """Check and preserve output files"""
    print("\n📁 Checking Output Files...")
    print("=" * 60)
    
    try:
        # Check for any video files in the container
        result = subprocess.run([
            "docker", "exec", "video-merger-api-celery-worker-1",
            "find", "/tmp", "-name", "*.mp4", "-o", "-name", "*.txt", "-o", "-name", "*.log"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            files = result.stdout.strip().split('\n')
            print(f"📁 Found {len(files)} output files:")
            
            for file_path in files:
                if file_path.strip():
                    print(f"   {file_path}")
                    
                    # Get file info
                    info_result = subprocess.run([
                        "docker", "exec", "video-merger-api-celery-worker-1",
                        "ls", "-lh", file_path
                    ], capture_output=True, text=True)
                    
                    if info_result.returncode == 0:
                        print(f"     {info_result.stdout.strip()}")
                    
                    # Copy output files to local directory for inspection
                    if file_path.endswith('.mp4'):
                        local_filename = f"output_{Path(file_path).name}"
                        copy_result = subprocess.run([
                            "docker", "cp", 
                            f"video-merger-api-celery-worker-1:{file_path}",
                            local_filename
                        ], capture_output=True, text=True)
                        
                        if copy_result.returncode == 0:
                            print(f"     ✅ Copied to local: {local_filename}")
                        else:
                            print(f"     ❌ Failed to copy: {copy_result.stderr}")
        else:
            print("📁 No output files found")
            
    except Exception as e:
        print(f"❌ Error checking files: {e}")

if __name__ == "__main__":
    print("🎬 Sample Video Processing Test")
    print("=" * 60)
    
    # Test simple merge
    merge_job_id = test_simple_merge_with_sample_videos()
    
    # Test auto-effects
    effects_job_id = test_auto_effects_with_sample_video()
    
    # Monitor jobs
    if merge_job_id:
        print(f"\n🔍 Monitoring merge job {merge_job_id}...")
        merge_status = monitor_job_progress(merge_job_id, max_wait_minutes=5)
    
    if effects_job_id:
        print(f"\n🔍 Monitoring auto-effects job {effects_job_id}...")
        effects_status = monitor_job_progress(effects_job_id, max_wait_minutes=5)
    
    # Check logs and files
    check_ffmpeg_logs()
    check_output_files()
    
    print("\n" + "=" * 60)
    print("🎯 Sample Video Processing Test Complete")
    print("📋 Check the FFmpeg logs above for processing details")
    print("📁 Check the current directory for copied output files")
    print("🎬 You can now inspect the actual video processing results!")
