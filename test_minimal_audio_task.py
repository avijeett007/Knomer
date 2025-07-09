#!/usr/bin/env python3
"""
Minimal test of audio separation task to isolate the .get() issue
"""

import sys
import os
from pathlib import Path
import tempfile
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery_app import celery_app
from services.audio_separator import AudioSeparator

@celery_app.task(queue="video_processing")
def minimal_audio_separation_task(video_path_str: str) -> dict:
    """Minimal audio separation task to test for .get() issues"""
    try:
        video_path = Path(video_path_str)
        temp_dir = Path(tempfile.mkdtemp(prefix="minimal_audio_test_"))
        
        print(f"Starting minimal audio separation for: {video_path}")
        
        # Initialize audio separator
        audio_separator = AudioSeparator()
        
        # Perform audio separation
        result = audio_separator.separate_audio_from_video(video_path, temp_dir / "output")
        
        print(f"Audio separation completed: {result['success']}")
        
        return {
            'success': result['success'],
            'message': 'Minimal audio separation completed',
            'temp_dir': str(temp_dir)
        }
        
    except Exception as e:
        print(f"Error in minimal audio separation: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def test_minimal_audio_task():
    """Test the minimal audio separation task"""
    print("🧪 Minimal Audio Separation Task Test")
    print("=" * 50)
    
    # Sample video path (inside Docker container)
    video_path = "/app/tests/sample_videos/Complete_Whitelabel_Is_Here.mov"
    
    try:
        # Submit the task
        print("🚀 Submitting minimal audio separation task...")
        task_result = minimal_audio_separation_task.delay(video_path)
        
        print(f"✅ Task submitted: {task_result.id}")
        
        # Monitor task progress
        print("⏳ Waiting for task completion...")
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while not task_result.ready():
            if time.time() - start_time > timeout:
                print("❌ Task timed out")
                return False
            
            print(f"   Task state: {task_result.state}")
            time.sleep(5)
        
        # Get result
        result = task_result.result
        
        if result['success']:
            print("✅ Minimal audio separation task completed successfully!")
            print(f"   Message: {result['message']}")
            return True
        else:
            print(f"❌ Minimal audio separation task failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during minimal task test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_minimal_audio_task()
    if success:
        print("\n🎉 Minimal audio separation task test passed!")
    else:
        print("\n💥 Minimal audio separation task test failed!")
    
    sys.exit(0 if success else 1)
