#!/usr/bin/env python3
"""
Simple test for enhanced auto-zoom using local test videos
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = "vp_UHUnroUYlsyEg8TD79ef4ApKarClmF9FXYH6ROSfM3g"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_zoom_keyword_detection():
    """Test the zoom keyword detection logic"""

    print("🔍 Testing Enhanced Zoom Keyword Detection")
    print("=" * 50)

    # Import the video processor to test keyword detection
    import sys
    sys.path.append('/app')

    try:
        from services.video_processor import VideoProcessor

        processor = VideoProcessor()

        # Test sentences with different types of expressions
        test_sentences = [
            "This is amazing and incredible!",
            "Pay attention to this important detail",
            "Let me show you how this works",
            "I'm so excited about this feature",
            "What do you think about this?",
            "This is a fast-moving action scene",
            "Here's our premium product showcase",
            "WOW! This is absolutely fantastic!",
            "Look at this crucial step carefully",
            "Watch how I demonstrate this technique"
        ]

        print("Testing keyword detection and intensity calculation:")
        detected_categories = set()

        for sentence in test_sentences:
            category = processor._detect_zoom_category(sentence.lower())
            intensity = processor._calculate_zoom_intensity(sentence.lower(), category) if category else 0

            print(f"   '{sentence}'")
            if category:
                pattern = processor.zoom_patterns[category]
                print(f"   → Category: {category}")
                print(f"   → Intensity: {intensity:.2f}")
                print(f"   → Zoom Type: {pattern['type']}")
                print(f"   → Zoom Range: {pattern['zoom_out']:.1f}x to {pattern['zoom_in'] * intensity:.1f}x")
                detected_categories.add(category)
            else:
                print(f"   → No zoom detected")
            print()

        print(f"✅ Detected {len(detected_categories)} different zoom categories:")
        for category in sorted(detected_categories):
            pattern = processor.zoom_patterns[category]
            print(f"   • {category}: {pattern['type']}")

        return len(detected_categories) > 0

    except Exception as e:
        print(f"❌ Keyword detection test failed: {str(e)}")
        return False

def test_auto_zoom_simple():
    """Test enhanced auto-zoom with a simple job"""
    
    print("🎬 Testing Enhanced Auto-Zoom (Simple Test)")
    print("=" * 50)
    
    # Simple test job
    job_data = {
        "job_type": "auto_effects",
        "videos": [
            {
                "url": "file:///app/tests/test_videos/sample1.mp4",
                "duration": 30.0,
                "order_index": 0
            }
        ],
        "processing_options": {
            "quality_preset": "balanced",
            "enable_transcription": True,
            "ai_effects_based_on_transcript": True,
            "auto_effects": True
        }
    }
    
    try:
        # Check credits first
        print("💳 Checking credits...")
        credits_response = requests.get(f"{BASE_URL}/credits", headers=HEADERS)
        if credits_response.status_code == 200:
            credits = credits_response.json()
            print(f"   Available credits: {credits['remaining_credits']}")
        
        # Estimate credits
        print("💰 Estimating credits...")
        estimate_response = requests.post(
            f"{BASE_URL}/credits/estimate",
            headers=HEADERS,
            json={
                "job_type": job_data['job_type'],
                "videos": job_data['videos'],
                "processing_options": job_data['processing_options']
            }
        )
        
        if estimate_response.status_code == 200:
            estimate = estimate_response.json()
            print(f"   Estimated credits: {estimate['estimated_credits']}")
        else:
            print(f"   ⚠️  Credit estimation failed: {estimate_response.status_code}")
            print(f"   Error: {estimate_response.text}")
        
        # Create job
        print("🚀 Creating auto-zoom job...")
        job_response = requests.post(f"{BASE_URL}/jobs", headers=HEADERS, json=job_data)
        
        if job_response.status_code != 200:
            print(f"❌ Job creation failed: {job_response.status_code}")
            print(f"Error: {job_response.text}")
            return False
        
        job_info = job_response.json()
        job_id = job_info['id']
        print(f"✅ Job created: {job_id}")
        
        # Monitor progress
        print("⏳ Monitoring job progress...")
        start_time = time.time()
        
        while time.time() - start_time < 300:  # 5 minute timeout
            status_response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                job_status = status_data['job']['status']
                
                print(f"   Status: {job_status}")
                
                if job_status == 'completed':
                    output_url = status_data['job'].get('output_file_url')
                    credits_used = status_data['job'].get('actual_credits_used')
                    
                    print(f"🎉 Job completed successfully!")
                    print(f"📁 Output: {output_url}")
                    print(f"💳 Credits used: {credits_used}")
                    
                    return True
                    
                elif job_status == 'failed':
                    error_msg = status_data['job'].get('error_message', 'Unknown error')
                    print(f"❌ Job failed: {error_msg}")
                    return False
                    
                elif job_status in ['pending', 'processing']:
                    time.sleep(10)
                else:
                    print(f"⚠️  Unknown status: {job_status}")
                    time.sleep(5)
            else:
                print(f"⚠️  Status check failed: {status_response.status_code}")
                time.sleep(5)
        
        print("⏰ Job timed out")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_zoom_keyword_detection():
    """Test the zoom keyword detection logic"""
    
    print("\n🔍 Testing Zoom Keyword Detection")
    print("=" * 40)
    
    # Import the video processor to test keyword detection
    import sys
    sys.path.append('/app')
    
    try:
        from services.video_processor import VideoProcessor
        
        processor = VideoProcessor()
        
        # Test sentences with different types of expressions
        test_sentences = [
            "This is amazing and incredible!",
            "Pay attention to this important detail",
            "Let me show you how this works",
            "I'm so excited about this feature",
            "What do you think about this?",
            "This is a fast-moving action scene",
            "Here's our premium product showcase"
        ]
        
        print("Testing keyword detection:")
        for sentence in test_sentences:
            category = processor._detect_zoom_category(sentence.lower())
            intensity = processor._calculate_zoom_intensity(sentence.lower(), category) if category else 0
            
            print(f"   '{sentence}'")
            print(f"   → Category: {category}, Intensity: {intensity:.2f}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Keyword detection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Enhanced Auto-Zoom Testing Suite")
    print("=" * 50)
    
    # Test keyword detection first
    keyword_test = test_zoom_keyword_detection()
    
    # Test actual auto-zoom processing
    if keyword_test:
        zoom_test = test_auto_zoom_simple()
        
        if zoom_test:
            print("\n🎉 All enhanced auto-zoom tests passed!")
            print("🔍 The new auto-zoom system includes:")
            print("   • Dynamic zoom patterns (pulse, smooth, quick)")
            print("   • Content-aware intensity adjustment")
            print("   • Multiple zoom categories (excitement, emphasis, etc.)")
            print("   • Transcript-driven timing")
        else:
            print("\n⚠️  Auto-zoom processing test failed")
    else:
        print("\n⚠️  Keyword detection test failed")
