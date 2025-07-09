#!/usr/bin/env python3
"""
Comprehensive API Test Suite
Tests all video processing features and generates output files
"""

import requests
import json
import time
import os
from pathlib import Path
import sys

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_RBxRfDbA1zm-EUgeeKkaVolIU8Z_T65mcAiyaVAmc7c"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Test files
TEST_FILES = {
    "large_video": "tests/sample_videos/Complete_Whitelabel_Is_Here.mov",
    "small_video1": "tests/sample_videos/Yetti_Patel_s_London_Vlog.mp4", 
    "small_video2": "tests/sample_videos/Yetti_Patel_s_UK_Tour_Intro.mp4",
    "transition": "tests/sample_videos/Animation_Transition.mp4",
    "logo": "tests/sample_videos/knolabslogo.png"
}

# Output directory
OUTPUT_DIR = Path("test_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🎬 {title}")
    print(f"{'='*60}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"🔍 {message}")

def download_output_file(output_url, filename):
    """Download output file to local machine"""
    try:
        print_info(f"Downloading {filename}...")
        response = requests.get(output_url, stream=True)
        if response.status_code == 200:
            output_path = OUTPUT_DIR / filename
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size = output_path.stat().st_size
            print_success(f"Downloaded {filename} ({file_size:,} bytes)")
            return True
        else:
            print_error(f"Download failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Download error: {e}")
        return False

def test_health_check():
    """Test API health check"""
    print_header("API Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy - Version {data['version']}")
            print_info(f"Services: {data['services']}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_user_credits():
    """Test user credits endpoint"""
    print_header("User Credits Check")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users/credits", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Available credits: {data['credits']}")
            return data['credits']
        else:
            print_error(f"Credits check failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Credits check error: {e}")
        return None

def test_simple_merge():
    """Test simple video merge (free tier)"""
    print_header("Simple Video Merge Test")
    try:
        files = [
            ('video_files', open(TEST_FILES["small_video1"], 'rb')),
            ('video_files', open(TEST_FILES["small_video2"], 'rb'))
        ]

        response = requests.post(f"{BASE_URL}/api/v1/merge", headers=HEADERS, files=files)

        # Close files
        for _, file_obj in files:
            file_obj.close()

        if response.status_code == 200:
            data = response.json()
            print_success(f"Simple merge job created: {data['job_id']}")
            print_info(f"Estimated credits: {data.get('estimated_credits', 0)}")

            # Download the output file
            if data.get('output_url') and data.get('output_file'):
                download_output_file(data['output_url'], data['output_file'])

            return data['job_id']
        else:
            print_error(f"Simple merge failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Simple merge error: {e}")
        return None

def test_transition_merge():
    """Test video merge with transitions"""
    print_header("Transition Video Merge Test")
    try:
        files = [
            ('video_files', open(TEST_FILES["small_video1"], 'rb')),
            ('video_files', open(TEST_FILES["small_video2"], 'rb')),
            ('transition_file', open(TEST_FILES["transition"], 'rb'))
        ]

        data = {
            'transition_type': 'custom',
            'transition_duration': '1.0'
        }

        response = requests.post(f"{BASE_URL}/api/v1/merge/transitions", headers=HEADERS, files=files, data=data)

        # Close files
        for _, file_obj in files:
            file_obj.close()

        if response.status_code == 200:
            result = response.json()
            print_success(f"Transition merge job created: {result['job_id']}")
            print_info(f"Estimated credits: {result.get('estimated_credits', 0)}")

            # Download the output file
            if result.get('output_url') and result.get('output_file'):
                download_output_file(result['output_url'], result['output_file'])

            return result['job_id']
        else:
            print_error(f"Transition merge failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Transition merge error: {e}")
        return None

def test_logo_overlay():
    """Test logo overlay feature"""
    print_header("Logo Overlay Test")
    try:
        files = {
            'video_file': open(TEST_FILES["small_video1"], 'rb'),
            'logo_file': open(TEST_FILES["logo"], 'rb')
        }
        
        data = {
            'position': 'top-right',
            'opacity': '0.8',
            'scale': '0.2'
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/logo-overlay", headers=HEADERS, files=files, data=data)
        
        # Close files
        files['video_file'].close()
        files['logo_file'].close()
            
        if response.status_code == 200:
            result = response.json()
            print_success(f"Logo overlay job created: {result['job_id']}")
            print_info(f"Estimated credits: {result.get('estimated_credits', 0)}")

            # Download the output file
            if result.get('output_url') and result.get('output_file'):
                download_output_file(result['output_url'], result['output_file'])

            return result['job_id']
        else:
            print_error(f"Logo overlay failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Logo overlay error: {e}")
        return None

def test_premium_credit_estimation():
    """Test premium processing credit estimation"""
    print_header("Premium Credit Estimation Test")
    try:
        files = {
            'video_file': open(TEST_FILES["large_video"], 'rb')
        }
        
        data = {
            'enable_smart_zooming': 'true',
            'enable_smart_captioning': 'true', 
            'enable_logo_overlay': 'true'
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/premium/estimate-credits", headers=HEADERS, files=files, data=data)
        
        # Close file
        files['video_file'].close()
            
        if response.status_code == 200:
            result = response.json()
            print_success(f"Credit estimation completed")
            print_info(f"Duration: {result['duration_minutes']:.2f} minutes")
            print_info(f"Estimated credits: {result['estimated_credits']}")
            print_info(f"Base credits: {result['base_credits']}")
            print_info(f"Feature multiplier: {result['feature_multiplier']}x")
            print_info(f"Complexity multiplier: {result['complexity_multiplier']}x")
            
            breakdown = result.get('breakdown', {})
            print_info("Credit breakdown:")
            for feature, cost in breakdown.items():
                print_info(f"  • {feature}: {cost} credits")
                
            return result
        else:
            print_error(f"Credit estimation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Credit estimation error: {e}")
        return None

def test_premium_processing():
    """Test premium AI processing"""
    print_header("Premium AI Processing Test")
    try:
        files = {
            'video_file': open(TEST_FILES["large_video"], 'rb'),
            'logo_file': open(TEST_FILES["logo"], 'rb')
        }
        
        data = {
            'enable_smart_zooming': 'true',
            'enable_smart_captioning': 'true',
            'enable_logo_overlay': 'true',
            'processing_quality': 'high'
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/premium/process", headers=HEADERS, files=files, data=data)
        
        # Close files
        files['video_file'].close()
        files['logo_file'].close()
            
        if response.status_code == 200:
            result = response.json()
            print_success(f"Premium processing job created: {result['job_id']}")
            print_info(f"Estimated credits: {result['estimated_credits']}")
            print_info(f"Duration: {result['duration_seconds']:.1f} seconds")

            features = result.get('features_enabled', {})
            print_info("Features enabled:")
            for feature, enabled in features.items():
                if enabled:
                    print_info(f"  • {feature.replace('_', ' ').title()}")

            # Show processing steps
            if result.get('processing_steps'):
                print_info("Processing steps applied:")
                for step in result['processing_steps']:
                    print_info(f"  • {step}")

            # Download the output file
            if result.get('output_url') and result.get('output_file'):
                download_output_file(result['output_url'], result['output_file'])

            return result['job_id']
        else:
            print_error(f"Premium processing failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Premium processing error: {e}")
        return None

def test_job_status(job_id, job_type="standard"):
    """Test job status monitoring"""
    print_header(f"Job Status Test - {job_type.title()}")
    try:
        if job_type == "premium":
            endpoint = f"{BASE_URL}/api/v1/premium/jobs/{job_id}"
        else:
            endpoint = f"{BASE_URL}/api/v1/jobs/{job_id}"
            
        response = requests.get(endpoint, headers=HEADERS)
            
        if response.status_code == 200:
            result = response.json()
            print_success(f"Job status retrieved: {result['status']}")
            print_info(f"Job ID: {result['job_id']}")
            print_info(f"Progress: {result.get('progress', 'N/A')}%")
            print_info(f"Message: {result.get('message', 'N/A')}")
            
            if result.get('output_url'):
                print_info(f"Output URL: {result['output_url']}")
                
            if result.get('credits_used'):
                print_info(f"Credits used: {result['credits_used']}")
                
            return result
        else:
            print_error(f"Job status failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print_error(f"Job status error: {e}")
        return None

def main():
    """Run comprehensive API tests"""
    print_header("Comprehensive Video Processing API Test Suite")
    print_info("Testing all features with output file generation")
    
    # Test results tracking
    results = {
        "health_check": False,
        "credits_available": 0,
        "simple_merge_job": None,
        "transition_merge_job": None,
        "logo_overlay_job": None,
        "premium_estimation": None,
        "premium_processing_job": None,
        "job_statuses": {}
    }
    
    # 1. Health Check
    results["health_check"] = test_health_check()
    if not results["health_check"]:
        print_error("API is not healthy. Stopping tests.")
        return False
    
    # 2. Check Credits
    results["credits_available"] = test_user_credits()
    if results["credits_available"] is None:
        print_error("Cannot check user credits. Stopping tests.")
        return False
    
    # 3. Simple Merge Test
    results["simple_merge_job"] = test_simple_merge()
    
    # 4. Transition Merge Test  
    results["transition_merge_job"] = test_transition_merge()
    
    # 5. Logo Overlay Test
    results["logo_overlay_job"] = test_logo_overlay()
    
    # 6. Premium Credit Estimation
    results["premium_estimation"] = test_premium_credit_estimation()
    
    # 7. Premium Processing Test
    results["premium_processing_job"] = test_premium_processing()
    
    # 8. Test Job Status for all created jobs
    job_tests = [
        ("simple_merge_job", "standard"),
        ("transition_merge_job", "standard"), 
        ("logo_overlay_job", "standard"),
        ("premium_processing_job", "premium")
    ]
    
    for job_key, job_type in job_tests:
        job_id = results.get(job_key)
        if job_id:
            status = test_job_status(job_id, job_type)
            results["job_statuses"][job_key] = status
    
    # Summary
    print_header("Test Results Summary")
    
    successful_tests = 0
    total_tests = 0
    
    # Count successful tests
    if results["health_check"]:
        successful_tests += 1
        print_success("Health check passed")
    total_tests += 1
    
    if results["credits_available"] is not None:
        successful_tests += 1
        print_success(f"Credits check passed - {results['credits_available']} credits available")
    total_tests += 1
    
    for job_key in ["simple_merge_job", "transition_merge_job", "logo_overlay_job", "premium_processing_job"]:
        if results[job_key]:
            successful_tests += 1
            print_success(f"{job_key.replace('_', ' ').title()} created successfully")
        total_tests += 1
    
    if results["premium_estimation"]:
        successful_tests += 1
        print_success("Premium credit estimation completed")
    total_tests += 1
    
    # Job status tests
    for job_key, status in results["job_statuses"].items():
        if status:
            successful_tests += 1
            print_success(f"{job_key.replace('_', ' ').title()} status retrieved")
        total_tests += 1
    
    print_header("Final Results")
    print_info(f"Tests passed: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print_success("🎉 ALL TESTS PASSED! 🎉")
        print_success("Video Processing API is fully functional!")
        return True
    else:
        print_error(f"Some tests failed ({total_tests - successful_tests} failures)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
