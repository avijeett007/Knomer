#!/usr/bin/env python3
"""
Premium Video Processing Test Suite

Tests the AI-powered premium video processing system with:
- Smart zooming based on AI analysis
- Intelligent captioning placement
- Logo overlay optimization
- Step-by-step progress tracking
- Retry and recovery mechanisms
"""

import requests
import json
import time
from pathlib import Path
import sys

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_2Lz2RTx9GS3CxkeCyRsl_Y_T3J1YOclGQY1KBjZY8ts"  # Update with your API key

# Test files
SAMPLE_VIDEO = Path("tests/sample_videos/Complete_Whitelabel_Is_Here.mov")
LOGO_FILE = Path("tests/sample_videos/knolabslogo.png")

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🎬 {title}")
    print(f"{'='*60}")

def print_step(step):
    """Print a formatted step"""
    print(f"\n🔍 {step}")

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print an info message"""
    print(f"   {message}")

def check_credits():
    """Check available credits"""
    print_step("Checking available credits...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/credits",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if response.status_code == 200:
            credits = response.json()
            available = credits['total_credits'] - credits['used_credits']
            print_success(f"Available credits: {available:,}")
            return available
        else:
            print_error(f"Could not check credits: {response.status_code}")
            print_info(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Credit check failed: {e}")
        return None

def estimate_premium_credits(enable_zooming=True, enable_captioning=True, enable_logo=True):
    """Estimate credits for premium processing"""
    print_step("Estimating premium processing credits...")
    
    try:
        with open(SAMPLE_VIDEO, 'rb') as video_file:
            files = {'video_file': video_file}
            data = {
                'enable_smart_zooming': enable_zooming,
                'enable_smart_captioning': enable_captioning,
                'enable_logo_overlay': enable_logo
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/premium/estimate-credits",
                headers={"Authorization": f"Bearer {API_KEY}"},
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            estimate = response.json()
            print_success(f"Estimated credits: {estimate['estimated_credits']:,}")
            print_info(f"Duration: {estimate['duration_minutes']:.2f} minutes")
            print_info(f"Base cost: {estimate['base_credits']} credits")
            print_info(f"Feature multiplier: {estimate['feature_multiplier']:.1f}x")
            print_info(f"Complexity multiplier: {estimate['complexity_multiplier']:.1f}x")
            
            print_info("📊 Breakdown:")
            for feature, cost in estimate['breakdown'].items():
                if cost > 0:
                    print_info(f"   • {feature.replace('_', ' ').title()}: {cost} credits")
            
            return estimate
        else:
            print_error(f"Credit estimation failed: {response.status_code}")
            print_info(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Credit estimation failed: {e}")
        return None

def create_premium_job(enable_zooming=True, enable_captioning=True, enable_logo=True):
    """Create a premium processing job"""
    print_step("Creating premium processing job...")
    
    try:
        files = {}
        data = {
            'enable_smart_zooming': enable_zooming,
            'enable_smart_captioning': enable_captioning,
            'enable_logo_overlay': enable_logo,
            'processing_quality': 'high'
        }
        
        # Add video file
        with open(SAMPLE_VIDEO, 'rb') as video_file:
            files['video_file'] = video_file
            
            # Add logo file if enabled
            if enable_logo and LOGO_FILE.exists():
                with open(LOGO_FILE, 'rb') as logo_file:
                    files['logo_file'] = logo_file
                    
                    response = requests.post(
                        f"{BASE_URL}/api/v1/premium/process",
                        headers={"Authorization": f"Bearer {API_KEY}"},
                        files=files,
                        data=data
                    )
            else:
                response = requests.post(
                    f"{BASE_URL}/api/v1/premium/process",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    files=files,
                    data=data
                )
        
        if response.status_code == 200:
            job = response.json()
            print_success(f"Premium job created: {job['job_id']}")
            print_info(f"Estimated credits: {job['estimated_credits']:,}")
            print_info(f"Duration: {job['duration_seconds']:.1f} seconds")
            
            features = job['features_enabled']
            print_info("🎯 Features enabled:")
            if features['smart_zooming']:
                print_info("   • Smart AI-powered zooming")
            if features['smart_captioning']:
                print_info("   • Intelligent captioning placement")
            if features['logo_overlay']:
                print_info("   • Optimized logo overlay")
            
            return job['job_id']
        else:
            print_error(f"Job creation failed: {response.status_code}")
            print_info(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Job creation failed: {e}")
        return None

def monitor_job_progress(job_id, timeout_minutes=30):
    """Monitor job progress with detailed step tracking"""
    print_step(f"Monitoring premium job progress: {job_id}")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    last_step = None
    
    while time.time() - start_time < timeout_seconds:
        try:
            # Get job status
            response = requests.get(
                f"{BASE_URL}/api/v1/premium/jobs/{job_id}",
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            
            if response.status_code == 200:
                job = response.json()
                status = job['status']
                
                # Get detailed progress
                progress_response = requests.get(
                    f"{BASE_URL}/api/v1/premium/jobs/{job_id}/progress",
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    current_step = progress.get('current_step')
                    progress_pct = progress.get('progress_percentage', 0)
                    
                    # Show progress update
                    if current_step != last_step:
                        step_name = current_step.replace('_', ' ').title() if current_step else 'Unknown'
                        print_info(f"📋 Step: {step_name} ({progress_pct:.1f}%)")
                        last_step = current_step
                    
                    # Show completed steps
                    completed_steps = progress.get('completed_steps', [])
                    if completed_steps:
                        completed_names = [step.replace('_', ' ').title() for step in completed_steps]
                        print_info(f"✅ Completed: {', '.join(completed_names[-3:])}")  # Show last 3
                
                if status == 'completed':
                    print_success("Premium processing completed!")
                    
                    # Show final results
                    if job.get('output_file_url'):
                        print_info(f"🎬 Output: {job['output_file_url']}")
                    
                    if job.get('actual_credits_used'):
                        print_info(f"💰 Credits used: {job['actual_credits_used']:,}")
                    
                    # Show AI analysis summary if available
                    if progress.get('ai_analysis_summary'):
                        ai_summary = progress['ai_analysis_summary']
                        print_info("🤖 AI Analysis Summary:")
                        print_info(f"   • Effects detected: {ai_summary.get('total_effects_detected', 0)}")
                        print_info(f"   • Complexity: {ai_summary.get('complexity', 'unknown')}")
                        print_info(f"   • AI confidence: {ai_summary.get('ai_confidence', 0):.1%}")
                    
                    return job
                    
                elif status == 'failed':
                    print_error("Premium processing failed!")
                    if job.get('error_message'):
                        print_info(f"Error: {job['error_message']}")
                    return None
                    
                elif status in ['pending', 'processing']:
                    # Continue monitoring
                    time.sleep(5)
                    continue
                    
            else:
                print_error(f"Failed to get job status: {response.status_code}")
                return None
                
        except Exception as e:
            print_error(f"Error monitoring job: {e}")
            time.sleep(5)
            continue
    
    print_error(f"Job timed out after {timeout_minutes} minutes")
    return None

def test_premium_processing():
    """Run comprehensive premium processing tests"""
    print_header("Premium AI Video Processing Test Suite")
    
    # Check prerequisites
    if not SAMPLE_VIDEO.exists():
        print_error(f"Sample video not found: {SAMPLE_VIDEO}")
        return False
    
    if not LOGO_FILE.exists():
        print_error(f"Logo file not found: {LOGO_FILE}")
        print_info("Logo overlay will be disabled")
        enable_logo = False
    else:
        enable_logo = True
    
    print_success(f"Sample video found: {SAMPLE_VIDEO.name}")
    if enable_logo:
        print_success(f"Logo file found: {LOGO_FILE.name}")
    
    # Test 1: Check credits
    available_credits = check_credits()
    if available_credits is None:
        return False
    
    # Test 2: Estimate credits
    estimate = estimate_premium_credits(
        enable_zooming=True,
        enable_captioning=True,
        enable_logo=enable_logo
    )
    
    if not estimate:
        return False
    
    if available_credits < estimate['estimated_credits']:
        print_error(f"Insufficient credits. Need: {estimate['estimated_credits']:,}, Have: {available_credits:,}")
        return False
    
    # Test 3: Create and process premium job
    job_id = create_premium_job(
        enable_zooming=True,
        enable_captioning=True,
        enable_logo=enable_logo
    )
    
    if not job_id:
        return False
    
    # Test 4: Monitor processing
    result = monitor_job_progress(job_id, timeout_minutes=30)
    
    if result:
        print_header("Premium Processing Test Results")
        print_success("All tests passed! 🎉")
        print_info("Premium AI video processing is working correctly")
        return True
    else:
        print_header("Premium Processing Test Results")
        print_error("Tests failed! ❌")
        return False

if __name__ == "__main__":
    success = test_premium_processing()
    sys.exit(0 if success else 1)
