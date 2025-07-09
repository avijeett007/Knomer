#!/usr/bin/env python3
"""
Create sample video outputs using FFmpeg directly with the sample videos.
This will show you exactly what the API produces.
"""

import subprocess
import json
from pathlib import Path

def get_video_info(video_path):
    """Get information about a video file"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json", 
            "-show_format", "-show_streams", str(video_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = float(info['format']['duration'])
            size = int(info['format']['size'])
            
            # Get video stream info
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                width = video_stream.get('width', 'Unknown')
                height = video_stream.get('height', 'Unknown')
                codec = video_stream.get('codec_name', 'Unknown')
                fps = video_stream.get('r_frame_rate', 'Unknown')
                
                return {
                    'duration': duration,
                    'size_mb': size / (1024 * 1024),
                    'resolution': f"{width}x{height}",
                    'codec': codec,
                    'fps': fps
                }
        
        return None
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def create_simple_merge():
    """Create a simple merge like the API does"""
    print("🎬 Creating Simple Video Merge (API Simulation)")
    print("=" * 50)
    
    # Use the sample videos we already have
    video1 = "output_Yetti_Patel_s_London_Vlog.mp4"
    video2 = "output_Yetti_Patel_s_UK_Tour_Intro.mp4"
    
    if not Path(video1).exists() or not Path(video2).exists():
        print("❌ Sample videos not found. Please run the previous test first.")
        return False
    
    print(f"📹 Input Video 1: {video1}")
    info1 = get_video_info(video1)
    if info1:
        print(f"   Duration: {info1['duration']:.2f}s, Size: {info1['size_mb']:.2f}MB")
        print(f"   Resolution: {info1['resolution']}, Codec: {info1['codec']}")
    
    print(f"📹 Input Video 2: {video2}")
    info2 = get_video_info(video2)
    if info2:
        print(f"   Duration: {info2['duration']:.2f}s, Size: {info2['size_mb']:.2f}MB")
        print(f"   Resolution: {info2['resolution']}, Codec: {info2['codec']}")
    
    # Create concat file (this is what the API does internally)
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        f.write(f"file '{video1}'\n")
        f.write(f"file '{video2}'\n")
    
    output_file = "api_style_merged_output.mp4"
    
    print(f"\n🔧 Running FFmpeg merge (same as API)...")
    
    # This is the exact command the API uses
    ffmpeg_cmd = [
        "ffmpeg", "-y",  # Overwrite output
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",  # Copy streams without re-encoding (fast)
        output_file
    ]
    
    print(f"💻 Command: {' '.join(ffmpeg_cmd)}")
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Merge completed successfully!")
            print(f"📁 Output file: {output_file}")
            
            # Get output info
            output_info = get_video_info(output_file)
            if output_info:
                print(f"📊 Output Details:")
                print(f"   Duration: {output_info['duration']:.2f}s")
                print(f"   Size: {output_info['size_mb']:.2f}MB")
                print(f"   Resolution: {output_info['resolution']}")
                print(f"   Codec: {output_info['codec']}")
                
                expected_duration = (info1['duration'] if info1 else 0) + (info2['duration'] if info2 else 0)
                print(f"   Expected Duration: {expected_duration:.2f}s")
                print(f"   ✅ Duration matches: {abs(output_info['duration'] - expected_duration) < 1.0}")
            
            return True
        else:
            print(f"❌ FFmpeg failed:")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running FFmpeg: {e}")
        return False
    finally:
        # Clean up concat file
        if Path(concat_file).exists():
            Path(concat_file).unlink()

def create_with_fade_transition():
    """Create a merge with fade transition (advanced API feature)"""
    print("\n🎬 Creating Merge with Fade Transition (Advanced API)")
    print("=" * 55)
    
    video1 = "output_Yetti_Patel_s_London_Vlog.mp4"
    video2 = "output_Yetti_Patel_s_UK_Tour_Intro.mp4"
    
    if not Path(video1).exists() or not Path(video2).exists():
        print("❌ Sample videos not found.")
        return False
    
    output_file = "api_style_fade_transition.mp4"
    
    print(f"🔧 Creating fade transition between videos...")
    
    # This is a more complex FFmpeg command for transitions
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", video1,
        "-i", video2,
        "-filter_complex",
        "[0:v][1:v]xfade=transition=fade:duration=1:offset=7[v];[0:a][1:a]acrossfade=d=1[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-c:a", "aac",
        output_file
    ]
    
    print(f"💻 Command: {' '.join(ffmpeg_cmd)}")
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Fade transition completed!")
            print(f"📁 Output file: {output_file}")
            
            # Get output info
            output_info = get_video_info(output_file)
            if output_info:
                print(f"📊 Output Details:")
                print(f"   Duration: {output_info['duration']:.2f}s")
                print(f"   Size: {output_info['size_mb']:.2f}MB")
                print(f"   Resolution: {output_info['resolution']}")
                print(f"   Codec: {output_info['codec']}")
            
            return True
        else:
            print(f"❌ FFmpeg failed:")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running FFmpeg: {e}")
        return False

def create_short_clips():
    """Create short clips from the sample videos for faster testing"""
    print("\n🎬 Creating Short Clips for Testing")
    print("=" * 40)
    
    # Create 5-second clips from the original videos
    original_videos = [
        "output_Yetti_Patel_s_London_Vlog.mp4",
        "output_Yetti_Patel_s_UK_Tour_Intro.mp4"
    ]
    
    short_clips = []
    
    for i, video in enumerate(original_videos):
        if Path(video).exists():
            output_clip = f"short_clip_{i+1}.mp4"
            
            # Create 5-second clip
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", video,
                "-t", "5",  # 5 seconds
                "-c", "copy",
                output_clip
            ]
            
            try:
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ Created: {output_clip}")
                    short_clips.append(output_clip)
                else:
                    print(f"❌ Failed to create {output_clip}")
            except Exception as e:
                print(f"❌ Error creating {output_clip}: {e}")
    
    return short_clips

def main():
    print("🎬 Video Processing Output Generator")
    print("=" * 50)
    print("This will create the same outputs that your API produces!")
    print()
    
    # Check if we have sample videos
    sample_videos = [
        "output_Yetti_Patel_s_London_Vlog.mp4",
        "output_Yetti_Patel_s_UK_Tour_Intro.mp4",
        "output_open_door_transition_first_clip.mp4"
    ]
    
    available_videos = [v for v in sample_videos if Path(v).exists()]
    
    if len(available_videos) < 2:
        print("❌ Need at least 2 sample videos.")
        print("💡 Please run the previous test script first to get sample videos.")
        return
    
    print(f"✅ Found {len(available_videos)} sample videos")
    
    # Create short clips for faster processing
    short_clips = create_short_clips()
    
    # Create simple merge (API style)
    success1 = create_simple_merge()
    
    # Create fade transition (advanced API style)
    success2 = create_with_fade_transition()
    
    print(f"\n" + "=" * 50)
    print("🎯 Output Generation Complete!")
    
    # List all created files
    output_files = [
        "api_style_merged_output.mp4",
        "api_style_fade_transition.mp4"
    ] + [f"short_clip_{i}.mp4" for i in range(1, 3)]
    
    print(f"\n📁 Generated Files:")
    for file in output_files:
        if Path(file).exists():
            info = get_video_info(file)
            print(f"   📹 {file}")
            if info:
                print(f"      Duration: {info['duration']:.2f}s, Size: {info['size_mb']:.2f}MB")
                print(f"      Resolution: {info['resolution']}")
            print(f"      ✅ Ready to play!")
    
    print(f"\n🎬 You can now play these files to see exactly what your API produces!")
    print(f"💡 These demonstrate the same FFmpeg operations your API performs.")

if __name__ == "__main__":
    main()
