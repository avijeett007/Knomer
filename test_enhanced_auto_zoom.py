#!/usr/bin/env python3
"""
Test the enhanced auto-zoom functionality with dynamic zoom effects
"""

import requests
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_UHUnroUYlsyEg8TD79ef4ApKarClmF9FXYH6ROSfM3g"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_enhanced_auto_zoom():
    """Test the enhanced auto-zoom with different types of expressive content"""
    
    print("🎬 Testing Enhanced Auto-Zoom with Dynamic Effects")
    print("=" * 60)
    
    # Test cases with different types of expressive language
    test_cases = [
        {
            "name": "Excitement & Emphasis",
            "description": "Test zoom effects for exciting and emphatic language",
            "job_data": {
                "job_type": "auto_effects",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_5mb.mp4",
                        "duration": 60.0,
                        "order_index": 0
                    }
                ],
                "processing_options": {
                    "quality_preset": "quality",
                    "enable_transcription": True,
                    "ai_effects_based_on_transcript": True,
                    "auto_effects": True,
                    "platform": "youtube"
                }
            }
        },
        {
            "name": "Tutorial Demonstration",
            "description": "Test smooth zoom for tutorial-style content",
            "job_data": {
                "job_type": "auto_effects",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
                        "duration": 45.0,
                        "order_index": 0
                    }
                ],
                "processing_options": {
                    "quality_preset": "balanced",
                    "enable_transcription": True,
                    "ai_effects_based_on_transcript": True,
                    "auto_effects": True,
                    "platform": "youtube"
                }
            }
        },
        {
            "name": "TikTok with Auto-Zoom",
            "description": "Test dynamic zoom with TikTok format conversion",
            "job_data": {
                "job_type": "auto_effects",
                "videos": [
                    {
                        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
                        "duration": 30.0,
                        "order_index": 0
                    }
                ],
                "processing_options": {
                    "quality_preset": "quality",
                    "enable_transcription": True,
                    "ai_effects_based_on_transcript": True,
                    "auto_effects": True,
                    "platform": "tiktok"
                }
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"📝 {test_case['description']}")
        
        try:
            # Estimate credits first
            print("   💰 Estimating credits...")
            estimate_response = requests.post(
                f"{BASE_URL}/credits/estimate",
                headers=HEADERS,
                json={
                    "job_type": test_case['job_data']['job_type'],
                    "videos": test_case['job_data']['videos'],
                    "processing_options": test_case['job_data']['processing_options']
                },
                timeout=10
            )
            
            if estimate_response.status_code == 200:
                estimate = estimate_response.json()
                print(f"   💳 Estimated credits: {estimate['estimated_credits']}")
            else:
                print(f"   ⚠️  Credit estimation failed: {estimate_response.status_code}")
            
            # Create job
            print("   🚀 Creating auto-zoom job...")
            job_response = requests.post(
                f"{BASE_URL}/jobs",
                headers=HEADERS,
                json=test_case['job_data'],
                timeout=10
            )
            
            if job_response.status_code != 200:
                print(f"   ❌ Job creation failed: {job_response.status_code}")
                print(f"      Error: {job_response.text}")
                results.append({
                    "test": test_case['name'],
                    "success": False,
                    "error": f"Job creation failed: {job_response.status_code}"
                })
                continue
            
            job_data = job_response.json()
            job_id = job_data['id']
            print(f"   📋 Job created: {job_id}")
            
            # Monitor job progress
            print("   ⏳ Monitoring job progress...")
            start_time = time.time()
            max_wait_time = 300  # 5 minutes
            
            while time.time() - start_time < max_wait_time:
                status_response = requests.get(
                    f"{BASE_URL}/jobs/{job_id}",
                    headers=HEADERS,
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    job_status = status_data['job']['status']
                    
                    if job_status == 'completed':
                        output_url = status_data['job'].get('output_file_url')
                        credits_used = status_data['job'].get('actual_credits_used')
                        processing_time = time.time() - start_time
                        
                        print(f"   ✅ Job completed successfully!")
                        print(f"   📁 Output: {output_url}")
                        print(f"   💳 Credits used: {credits_used}")
                        print(f"   ⏱️  Processing time: {processing_time:.1f}s")
                        
                        results.append({
                            "test": test_case['name'],
                            "success": True,
                            "job_id": job_id,
                            "output_url": output_url,
                            "credits_used": credits_used,
                            "processing_time": processing_time
                        })
                        break
                        
                    elif job_status == 'failed':
                        error_msg = status_data['job'].get('error_message', 'Unknown error')
                        print(f"   ❌ Job failed: {error_msg}")
                        results.append({
                            "test": test_case['name'],
                            "success": False,
                            "error": error_msg
                        })
                        break
                        
                    elif job_status in ['pending', 'processing']:
                        print(f"   🔄 Status: {job_status}")
                        time.sleep(10)
                    else:
                        print(f"   ⚠️  Unknown status: {job_status}")
                        time.sleep(5)
                else:
                    print(f"   ⚠️  Status check failed: {status_response.status_code}")
                    time.sleep(5)
            else:
                print(f"   ⏰ Job timed out after {max_wait_time}s")
                results.append({
                    "test": test_case['name'],
                    "success": False,
                    "error": "Job timed out"
                })
        
        except Exception as e:
            print(f"   ❌ Test failed with exception: {str(e)}")
            results.append({
                "test": test_case['name'],
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Enhanced Auto-Zoom Test Results")
    print("=" * 60)
    
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    
    print(f"✅ Successful Tests: {successful_tests}/{total_tests}")
    print(f"🎯 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests > 0:
        avg_processing_time = sum(r.get('processing_time', 0) for r in results if r['success']) / successful_tests
        total_credits = sum(r.get('credits_used', 0) for r in results if r['success'])
        
        print(f"⏱️  Average Processing Time: {avg_processing_time:.1f}s")
        print(f"💳 Total Credits Used: {total_credits}")
    
    print("\n📁 Generated Videos with Enhanced Auto-Zoom:")
    for result in results:
        if result['success']:
            print(f"   🎬 {result['test']}: {result.get('output_url', 'N/A')}")
        else:
            print(f"   ❌ {result['test']}: {result.get('error', 'Failed')}")
    
    if successful_tests == total_tests:
        print("\n🎉 All enhanced auto-zoom tests passed!")
        print("🔍 Check the output videos to see the dynamic zoom effects:")
        print("   • Quick pulse zooms for exciting words")
        print("   • Smooth zooms for demonstrations")
        print("   • Dynamic zooms for action words")
        print("   • Professional zooms for showcases")
    else:
        print(f"\n⚠️  {total_tests - successful_tests} test(s) failed.")
        print("🔧 Check the error messages above for details.")
    
    return results

if __name__ == "__main__":
    test_enhanced_auto_zoom()
