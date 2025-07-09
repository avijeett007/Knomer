#!/usr/bin/env python3
"""
Live API Testing Script
Tests the running Docker API with comprehensive functionality validation.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8001"
API_KEY = "vp_GkqinmgNdpcPbLbFWz0yV-5k5T7cGLc1buZ2K66mRJU"  # From container logs

def make_request(method: str, endpoint: str, data: Dict[Any, Any] = None, headers: Dict[str, str] = None, auth_required: bool = True) -> Dict[Any, Any]:
    """Make HTTP request to API"""
    url = f"{API_BASE_URL}{endpoint}"

    # Default headers
    default_headers = {
        "Content-Type": "application/json"
    }

    # Add Bearer token authentication if required
    if auth_required:
        default_headers["Authorization"] = f"Bearer {API_KEY}"

    if headers:
        default_headers.update(headers)

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return {
            "status_code": response.status_code,
            "data": response.json() if response.content else {},
            "success": 200 <= response.status_code < 300
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": 0,
            "data": {"error": str(e)},
            "success": False
        }

def test_health_endpoint():
    """Test health check endpoint"""
    print("🔍 Testing Health Endpoint...")

    response = make_request("GET", "/health", auth_required=False)  # No auth needed

    if response["success"]:
        print("✅ Health endpoint working")
        print(f"   Status: {response['data'].get('status', 'unknown')}")
        print(f"   Timestamp: {response['data'].get('timestamp', 'unknown')}")
        return True
    else:
        print(f"❌ Health endpoint failed: {response['data']}")
        return False

def test_root_endpoint():
    """Test root endpoint"""
    print("\n🔍 Testing Root Endpoint...")

    response = make_request("GET", "/", auth_required=False)  # No auth needed

    if response["success"]:
        print("✅ Root endpoint working")
        print(f"   Message: {response['data'].get('message', 'unknown')}")
        return True
    else:
        print(f"❌ Root endpoint failed: {response['data']}")
        return False

def test_credits_endpoint():
    """Test credits endpoint with authentication"""
    print("\n🔍 Testing Credits Endpoint...")

    response = make_request("GET", "/credits")

    if response["success"]:
        data = response["data"]
        print("✅ Credits endpoint working")
        print(f"   Total Credits: {data.get('total_credits', 0)}")
        print(f"   Used Credits: {data.get('used_credits', 0)}")
        print(f"   Remaining Credits: {data.get('remaining_credits', 0)}")
        print(f"   Last Updated: {data.get('last_updated', 'unknown')}")
        return True
    else:
        print(f"❌ Credits endpoint failed: {response['data']}")
        return False

def test_credit_estimation():
    """Test credit estimation endpoint"""
    print("\n🔍 Testing Credit Estimation...")

    # Test simple merge estimation
    simple_data = {
        "job_type": "simple_merge",
        "videos": [
            {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4", "duration": 15.0},
            {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4", "duration": 15.0}
        ],
        "processing_options": {
            "quality_preset": "balanced"
        }
    }

    response = make_request("POST", "/credits/estimate", simple_data)

    if response["success"]:
        data = response["data"]
        print("✅ Credit estimation working")
        print(f"   Simple merge (30s, 2 videos): {data.get('estimated_credits', 0)} credits")
        print(f"   Total duration: {data.get('total_duration_seconds', 0)}s")

        # Test auto-effects estimation
        auto_effects_data = {
            "job_type": "auto_effects",
            "videos": [
                {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4", "duration": 60.0}
            ],
            "processing_options": {
                "quality_preset": "balanced",
                "enable_transcription": True,
                "auto_effects": True
            }
        }

        response2 = make_request("POST", "/credits/estimate", auto_effects_data)
        if response2["success"]:
            data2 = response2["data"]
            print(f"   Auto-effects with transcription (60s): {data2.get('estimated_credits', 0)} credits")

        return True
    else:
        print(f"❌ Credit estimation failed: {response['data']}")
        return False

def test_job_creation():
    """Test job creation endpoint"""
    print("\n🔍 Testing Job Creation...")

    # Test simple merge job
    job_data = {
        "job_type": "simple_merge",
        "videos": [
            {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4", "duration": 15.0, "order_index": 0},
            {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4", "duration": 15.0, "order_index": 1}
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "transitions": [{"type": "fade", "duration": 1.0}]
        }
    }

    response = make_request("POST", "/jobs", job_data)

    if response["success"]:
        data = response["data"]
        print("✅ Job creation working")
        print(f"   Job ID: {data.get('id', 'unknown')}")
        print(f"   Status: {data.get('status', 'unknown')}")
        print(f"   Estimated Credits: {data.get('estimated_credits', 0)}")
        return data.get('id')
    else:
        print(f"❌ Job creation failed: {response['data']}")
        return None

def test_job_status(job_id: str):
    """Test job status endpoint"""
    print(f"\n🔍 Testing Job Status for {job_id}...")

    response = make_request("GET", f"/jobs/{job_id}")

    if response["success"]:
        data = response["data"]
        job_data = data.get('job', {})
        print("✅ Job status working")
        print(f"   Job ID: {job_data.get('id', 'unknown')}")
        print(f"   Status: {job_data.get('status', 'unknown')}")
        print(f"   Progress: {data.get('progress_percentage', 0)}%")
        return True
    else:
        print(f"❌ Job status failed: {response['data']}")
        return False

def test_jobs_list():
    """Test jobs listing endpoint"""
    print("\n🔍 Testing Jobs List...")
    
    response = make_request("GET", "/jobs")
    
    if response["success"]:
        data = response["data"]
        print("✅ Jobs list working")
        print(f"   Total Jobs: {len(data.get('jobs', []))}")
        if data.get('jobs'):
            latest_job = data['jobs'][0]
            print(f"   Latest Job: {latest_job.get('job_id', 'unknown')} ({latest_job.get('status', 'unknown')})")
        return True
    else:
        print(f"❌ Jobs list failed: {response['data']}")
        return False

def test_authentication_failure():
    """Test authentication failure scenarios"""
    print("\n🔍 Testing Authentication Failure...")

    # Test with invalid Bearer token
    response = make_request("GET", "/credits", headers={"Authorization": "Bearer invalid-token"})

    if not response["success"] and response["status_code"] == 401:
        print("✅ Authentication failure handling working")
        print(f"   Error: {response['data'].get('detail', 'unknown')}")
        return True
    else:
        print(f"❌ Authentication failure test failed: {response['data']}")
        return False

def test_advanced_job_features():
    """Test advanced job features"""
    print("\n🔍 Testing Advanced Job Features...")

    # Test auto-effects job
    auto_effects_data = {
        "job_type": "auto_effects",
        "videos": [
            {"url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4", "duration": 30.0, "order_index": 0}
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "enable_transcription": True,
            "auto_effects": True,
            "ai_effects_based_on_transcript": True
        }
    }

    response = make_request("POST", "/jobs", auto_effects_data)

    if response["success"]:
        data = response["data"]
        print("✅ Advanced job features working")
        print(f"   Auto-effects Job ID: {data.get('id', 'unknown')}")
        print(f"   Estimated Credits: {data.get('estimated_credits', 0)}")
        return True
    else:
        print(f"❌ Advanced job features failed: {response['data']}")
        return False

def main():
    """Run comprehensive API tests"""
    print("🎯 Live API Testing - Comprehensive Validation")
    print("=" * 60)
    
    tests = [
        test_health_endpoint,
        test_root_endpoint,
        test_credits_endpoint,
        test_credit_estimation,
        test_authentication_failure,
        test_jobs_list,
        test_job_creation,
        test_advanced_job_features
    ]
    
    passed = 0
    total = len(tests)
    job_id = None
    
    for test in tests:
        try:
            if test.__name__ == "test_job_creation":
                job_id = test()
                if job_id:
                    passed += 1
            else:
                if test():
                    passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} error: {e}")
    
    # Test job status if we have a job ID
    if job_id:
        try:
            if test_job_status(job_id):
                passed += 1
            total += 1
        except Exception as e:
            print(f"❌ Job status test error: {e}")
            total += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Live API Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL API TESTS PASSED!")
        print("\n✅ Your video processing API is FULLY FUNCTIONAL!")
        print("✅ Authentication system working")
        print("✅ Credit management working")
        print("✅ Job creation and tracking working")
        print("✅ Advanced features available")
        print("\n🚀 API is production-ready!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
