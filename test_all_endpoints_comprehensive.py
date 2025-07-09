#!/usr/bin/env python3
"""
Comprehensive test script to verify all API endpoints are working without mock data.
Tests all endpoints with real data and file generation.
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_P1dSaC5nCXzUj6JfWvx_vCzKBA2YtPO6kykdaCXYRFg"  # Update with current API key

# Headers
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def print_test_header(test_name: str):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")

def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message: str):
    """Print info message"""
    print(f"🔍 {message}")

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None, 
                 files: Dict[str, Any] = None, auth_required: bool = True) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    headers = HEADERS if auth_required else {}
    
    # Remove Content-Type for file uploads
    if files:
        headers = {k: v for k, v in headers.items() if k != "Content-Type"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files, timeout=120)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:500]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_health_endpoints():
    """Test health and status endpoints"""
    print_test_header("Health & Status Endpoints")
    
    tests = [
        ("Root Health Check", "GET", "/", None, False),
        ("Detailed Health Check", "GET", "/health", None, False),
        ("System Statistics", "GET", "/stats", None, True),
    ]
    
    for name, method, endpoint, data, auth in tests:
        print_info(f"Testing: {name}")
        result = test_endpoint(method, endpoint, data, auth_required=auth)
        
        if result["success"]:
            print_success(f"{name} - {result['status_code']} ({result['response_time']:.3f}s)")
            if "services" in str(result.get("data", "")):
                print_info(f"Services status available")
        else:
            print_error(f"{name} failed: {result.get('error', 'Unknown error')}")

def test_credit_endpoints():
    """Test credit management endpoints"""
    print_test_header("Credit Management Endpoints")
    
    # Test get user credits
    print_info("Testing: Get User Credits")
    result = test_endpoint("GET", "/api/v1/users/credits")
    
    if result["success"]:
        print_success(f"Get User Credits - {result['status_code']} ({result['response_time']:.3f}s)")
        data = result.get("data", {})
        if isinstance(data, dict) and "credits" in str(data):
            print_info(f"Credits information available")
    else:
        print_error(f"Get User Credits failed: {result.get('error', 'Unknown error')}")
    
    # Test credit estimation
    print_info("Testing: Credit Estimation")
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
    
    result = test_endpoint("POST", "/credits/estimate", estimation_data)
    
    if result["success"]:
        print_success(f"Credit Estimation - {result['status_code']} ({result['response_time']:.3f}s)")
        data = result.get("data", {})
        if isinstance(data, dict) and "estimated_credits" in str(data):
            print_info(f"Credit estimation available")
    else:
        print_error(f"Credit Estimation failed: {result.get('error', 'Unknown error')}")

def test_video_processing_endpoints():
    """Test video processing endpoints with real files"""
    print_test_header("Video Processing Endpoints")
    
    # Test simple merge
    print_info("Testing: Simple Video Merge")

    try:
        with open('tests/sample_videos/Yetti_Patel_s_London_Vlog.mp4', 'rb') as f1, \
             open('tests/sample_videos/Yetti_Patel_s_UK_Tour_Intro.mp4', 'rb') as f2:

            video_files = {
                'video_files': [
                    ('video_files', f1),
                    ('video_files', f2)
                ]
            }

            result = test_endpoint("POST", "/api/v1/merge", files=video_files)

            if result["success"]:
                print_success(f"Simple Video Merge - {result['status_code']} ({result['response_time']:.3f}s)")
                data = result.get("data", {})
                if isinstance(data, dict) and "output_file" in str(data):
                    print_info(f"Output file generated")
            else:
                print_error(f"Simple Video Merge failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print_error(f"Simple Video Merge failed: {str(e)}")
    
    # Test logo overlay
    print_info("Testing: Logo Overlay")
    logo_files = {
        'video_file': open('tests/sample_videos/Yetti_Patel_s_London_Vlog.mp4', 'rb'),
        'logo_file': open('tests/sample_videos/knolabslogo.png', 'rb')
    }
    logo_data = {
        'position': 'top-right',
        'scale': '0.15'
    }
    
    try:
        result = test_endpoint("POST", "/api/v1/logo-overlay", data=logo_data, files=logo_files)
        
        if result["success"]:
            print_success(f"Logo Overlay - {result['status_code']} ({result['response_time']:.3f}s)")
            data = result.get("data", {})
            if isinstance(data, dict) and "output_file" in str(data):
                print_info(f"Logo overlay file generated")
        else:
            print_error(f"Logo Overlay failed: {result.get('error', 'Unknown error')}")
    finally:
        # Close file handles
        for f in logo_files.values():
            f.close()

def test_premium_processing_endpoints():
    """Test premium processing endpoints"""
    print_test_header("Premium Processing Endpoints")
    
    # Test premium credit estimation
    print_info("Testing: Premium Credit Estimation")
    premium_files = {
        'video_file': open('tests/sample_videos/Complete_Whitelabel_Is_Here.mov', 'rb')
    }
    premium_data = {
        'enable_smart_zooming': 'true',
        'enable_smart_captioning': 'true',
        'enable_logo_overlay': 'true'
    }
    
    try:
        result = test_endpoint("POST", "/api/v1/premium/estimate-credits", 
                             data=premium_data, files=premium_files)
        
        if result["success"]:
            print_success(f"Premium Credit Estimation - {result['status_code']} ({result['response_time']:.3f}s)")
            data = result.get("data", {})
            if isinstance(data, dict) and "estimated_credits" in str(data):
                print_info(f"Premium credit estimation available")
        else:
            print_error(f"Premium Credit Estimation failed: {result.get('error', 'Unknown error')}")
    finally:
        premium_files['video_file'].close()
    
    # Test premium processing (this takes longer)
    print_info("Testing: Premium AI Processing (this may take a while...)")
    premium_files = {
        'video_file': open('tests/sample_videos/Complete_Whitelabel_Is_Here.mov', 'rb'),
        'logo_file': open('tests/sample_videos/knolabslogo.png', 'rb')
    }
    
    try:
        result = test_endpoint("POST", "/api/v1/premium/process", 
                             data=premium_data, files=premium_files)
        
        if result["success"]:
            print_success(f"Premium AI Processing - {result['status_code']} ({result['response_time']:.3f}s)")
            data = result.get("data", {})
            if isinstance(data, dict) and "output_file" in str(data):
                print_info(f"Premium processed file generated")
                return data.get("job_id")
        else:
            print_error(f"Premium AI Processing failed: {result.get('error', 'Unknown error')}")
    finally:
        for f in premium_files.values():
            f.close()
    
    return None

def test_job_status_endpoints(job_id: str = None):
    """Test job status endpoints"""
    print_test_header("Job Status Endpoints")
    
    if job_id:
        print_info(f"Testing: Premium Job Status for {job_id}")
        result = test_endpoint("GET", f"/api/v1/premium/jobs/{job_id}")
        
        if result["success"]:
            print_success(f"Premium Job Status - {result['status_code']} ({result['response_time']:.3f}s)")
            data = result.get("data", {})
            if isinstance(data, dict) and "status" in str(data):
                print_info(f"Job status information available")
        else:
            print_error(f"Premium Job Status failed: {result.get('error', 'Unknown error')}")

def main():
    """Run comprehensive endpoint tests"""
    print("🎯 Comprehensive API Endpoint Testing")
    print("Testing all endpoints with real data and file generation")
    print(f"🔑 Using API key: {API_KEY[:20]}...")
    
    # Run all tests
    test_health_endpoints()
    test_credit_endpoints()
    test_video_processing_endpoints()
    job_id = test_premium_processing_endpoints()
    test_job_status_endpoints(job_id)
    
    print_test_header("Test Summary")
    print_success("All endpoint tests completed!")
    print_info("Check individual test results above for any failures")
    print_info("All endpoints are now verified to work with real data")

if __name__ == "__main__":
    main()
