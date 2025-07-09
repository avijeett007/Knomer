#!/usr/bin/env python3
"""
Direct test of audio separator without Celery
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.audio_separator import AudioSeparator

def test_audio_separator_direct():
    """Test audio separator directly without Celery"""
    print("🧪 Direct Audio Separator Test")
    print("=" * 50)
    
    # Sample video path
    video_path = Path("/Users/avijitsarkar/Projects/Knotie-AI/video-merger-api/tests/sample_videos/Complete_Whitelabel_Is_Here.mov")
    
    if not video_path.exists():
        print(f"❌ Sample video not found: {video_path}")
        return False
    
    print(f"✅ Sample video found: {video_path.name}")
    
    # Create output directory
    output_dir = Path("/tmp/direct_audio_test")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize audio separator
        print("🔧 Initializing audio separator...")
        audio_separator = AudioSeparator()
        
        # Perform audio separation
        print("🎵 Starting audio separation...")
        result = audio_separator.separate_audio_from_video(video_path, output_dir)
        
        if result['success']:
            print("✅ Audio separation successful!")
            print(f"   📁 Output directory: {result['output_directory']}")
            print(f"   🎤 Voice track: {result['separated_voice']}")
            print(f"   🎶 Music track: {result['separated_music']}")
            print(f"   📊 Quality score: {result['analysis'].get('quality_score', 'N/A')}")
            return True
        else:
            print(f"❌ Audio separation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during audio separation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_audio_separator_direct()
    if success:
        print("\n🎉 Direct audio separator test passed!")
    else:
        print("\n💥 Direct audio separator test failed!")
    
    sys.exit(0 if success else 1)
