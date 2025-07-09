#!/usr/bin/env python3
"""
Quick test script to validate all Postman collection endpoints are working.
This ensures the Postman collection will work correctly.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_UHUnroUYlsyEg8TD79ef4ApKarClmF9FXYH6ROSfM3g"

# Headers
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None, auth_required: bool = True) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    headers = HEADERS if auth_required else {"Content-Type": "application/json"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Test all Postman collection endpoints"""
    print("🧪 Testing Postman Collection Endpoints")
    print("=" * 50)
    
    # Test cases matching Postman collection
    test_cases = [
        # Health & Status
        {
            "name": "Root Health Check",
            "method": "GET",
            "endpoint": "/",
            "auth_required": False
        },
        {
            "name": "Detailed Health Check",
            "method": "GET",
            "endpoint": "/health",
            "auth_required": False
        },
        {
            "name": "System Statistics",
            "method": "GET",
            "endpoint": "/stats",
            "auth_required": True
        },
        
        # Credit Management
        {
            "name": "Get User Credits",
            "method": "GET",
            "endpoint": "/credits",
            "auth_required": True
        },
        {
            "name": "Estimate Credits - Simple Merge",
            "method": "POST",
            "endpoint": "/credits/estimate",
            "auth_required": True,
            "data": {
                "job_type": "simple_merge",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
                        "duration": 30.0,
                        "order_index": 0
                    },
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
                        "duration": 25.0,
                        "order_index": 1
                    }
                ],
                "processing_options": {
                    "quality_preset": "balanced",
                    "transitions": [{"type": "fade", "duration": 1.0}]
                }
            }
        },
        {
            "name": "Estimate Credits - Auto Effects",
            "method": "POST",
            "endpoint": "/credits/estimate",
            "auth_required": True,
            "data": {
                "job_type": "auto_effects",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_5mb.mp4",
                        "duration": 120.0,
                        "order_index": 0
                    }
                ],
                "processing_options": {
                    "quality_preset": "high",
                    "enable_transcription": True,
                    "ai_effects_based_on_transcript": True,
                    "platform": "tiktok"
                }
            }
        },
        
        # Job Management
        {
            "name": "Create Simple Merge Job",
            "method": "POST",
            "endpoint": "/jobs",
            "auth_required": True,
            "data": {
                "job_type": "simple_merge",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
                        "duration": 30.0,
                        "order_index": 0
                    },
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
                        "duration": 25.0,
                        "order_index": 1
                    }
                ],
                "processing_options": {
                    "quality_preset": "balanced",
                    "transitions": [{"type": "fade", "duration": 1.0}]
                }
            }
        },
        {
            "name": "List User Jobs",
            "method": "GET",
            "endpoint": "/jobs?page=1&page_size=10",
            "auth_required": True
        }
    ]
    
    # Run tests
    results = []
    job_id = None
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        
        result = test_endpoint(
            method=test_case['method'],
            endpoint=test_case['endpoint'],
            data=test_case.get('data'),
            auth_required=test_case.get('auth_required', True)
        )
        
        # Save job ID for status checking
        if test_case['name'] == "Create Simple Merge Job" and result['success']:
            job_id = result['data'].get('id')
            print(f"   💾 Saved Job ID: {job_id}")
        
        # Display result
        if result['success']:
            print(f"   ✅ Success ({result['status_code']}) - {result['response_time']:.3f}s")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            if 'status_code' in result:
                print(f"      Status: {result['status_code']}")
        
        results.append({
            "test": test_case['name'],
            "success": result['success'],
            "response_time": result.get('response_time', 0)
        })
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Test job status if we have a job ID
    if job_id:
        print(f"\n🔍 Testing: Get Job Status")
        result = test_endpoint("GET", f"/jobs/{job_id}")
        if result['success']:
            print(f"   ✅ Success ({result['status_code']}) - {result['response_time']:.3f}s")
            job_status = result['data'].get('job', {}).get('status', 'unknown')
            print(f"   📊 Job Status: {job_status}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        results.append({
            "test": "Get Job Status",
            "success": result['success'],
            "response_time": result.get('response_time', 0)
        })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    avg_response_time = sum(r['response_time'] for r in results if r['response_time'] > 0) / max(1, len([r for r in results if r['response_time'] > 0]))
    
    print(f"✅ Successful Tests: {successful_tests}/{total_tests}")
    print(f"⏱️  Average Response Time: {avg_response_time:.3f}s")
    print(f"🎯 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 All tests passed! Your Postman collection is ready to use.")
        print("📋 Import the collection files into Postman and start testing!")
    else:
        print("\n⚠️  Some tests failed. Check the API status and try again.")
        print("🔧 Failed tests:")
        for result in results:
            if not result['success']:
                print(f"   ❌ {result['test']}")
    
    print(f"\n📁 Postman Files Created:")
    print(f"   📦 Video_Processing_API.postman_collection.json")
    print(f"   🌍 Video_Processing_API_Local.postman_environment.json")
    print(f"   🌍 Video_Processing_API_Production.postman_environment.json")
    print(f"   📖 POSTMAN_TESTING_GUIDE.md")

if __name__ == "__main__":
    main()
