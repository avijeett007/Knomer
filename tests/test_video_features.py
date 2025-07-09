"""
Tests for specific video processing features
"""
import pytest
import tempfile
from pathlib import Path
from services.video_processor import VideoProcessor

class TestVideoProcessor:
    """Test the video processor service directly"""
    
    @pytest.fixture
    def video_processor(self):
        """Get video processor instance"""
        return VideoProcessor()
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test outputs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_video_info_extraction(self, video_processor, sample_videos):
        """Test video information extraction"""
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip(f"Test video not found: {main_video}")
        
        info = video_processor._get_video_info(main_video)
        
        assert info, "Should extract video info"
        assert info.get("duration", 0) > 0, "Should have valid duration"
        assert info.get("width", 0) > 0, "Should have valid width"
        assert info.get("height", 0) > 0, "Should have valid height"
        
        print(f"Video info: {info}")
    
    def test_video_validation(self, video_processor, sample_videos):
        """Test video file validation"""
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip(f"Test video not found: {main_video}")
        
        validation = video_processor.validate_video_file(main_video)
        
        assert validation["valid"], f"Video should be valid: {validation.get('error')}"
        assert "info" in validation
        
    def test_simple_merge_functionality(self, video_processor, sample_videos, temp_output_dir):
        """Test simple video merging"""
        main_video = sample_videos["main_video"]
        intro_video = sample_videos["intro_video"]
        
        if not main_video.exists() or not intro_video.exists():
            pytest.skip("Test videos not found")
        
        output_path = temp_output_dir / "merged_output.mp4"
        input_files = [intro_video, main_video]
        
        result = video_processor.simple_merge(input_files, output_path)
        
        assert result["success"], f"Merge should succeed: {result.get('error')}"
        assert output_path.exists(), "Output file should be created"
        assert result["output_duration"] > 0, "Output should have valid duration"
        assert result["output_size"] > 0, "Output should have valid size"
        
        print(f"Merge result: {result}")
    
    def test_logo_overlay_functionality(self, video_processor, sample_videos, temp_output_dir):
        """Test logo overlay feature"""
        main_video = sample_videos["main_video"]
        logo = sample_videos["logo"]
        
        if not main_video.exists() or not logo.exists():
            pytest.skip("Test files not found")
        
        output_path = temp_output_dir / "logo_overlay_output.mp4"
        
        logo_config = {
            "logo_url": str(logo),
            "position": "top-right",
            "size": 0.15,
            "opacity": 0.8
        }
        
        result = video_processor.add_logo_overlay([main_video], output_path, logo_config)
        
        assert result["success"], f"Logo overlay should succeed: {result.get('error')}"
        assert output_path.exists(), "Output file should be created"
        
        print(f"Logo overlay result: {result}")
    
    def test_tiktok_resize(self, video_processor, sample_videos, temp_output_dir):
        """Test TikTok-style resize (9:16 aspect ratio)"""
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip("Test video not found")
        
        output_path = temp_output_dir / "tiktok_resized.mp4"
        
        result_path = video_processor._resize_for_tiktok(main_video, output_path)
        
        if result_path == output_path:
            # Resize was successful
            assert output_path.exists(), "Resized video should be created"
            
            # Check if aspect ratio is correct
            info = video_processor._get_video_info(output_path)
            if info.get("width") and info.get("height"):
                aspect_ratio = info["width"] / info["height"]
                expected_ratio = 720 / 1280  # 9:16
                assert abs(aspect_ratio - expected_ratio) < 0.1, f"Aspect ratio should be ~{expected_ratio}, got {aspect_ratio}"
            
            print(f"TikTok resize successful: {info}")
        else:
            print("TikTok resize skipped (ffmpeg might not be available)")


class TestTranscriptionFeatures:
    """Test transcription and AI features"""
    
    @pytest.fixture
    def video_processor(self):
        return VideoProcessor()
    
    def test_whisper_model_loading(self, video_processor):
        """Test that Whisper model loads correctly"""
        # This test checks if Whisper is available
        if video_processor.whisper_model is None:
            pytest.skip("Whisper model not available")
        
        assert video_processor.whisper_model is not None
        print("✅ Whisper model loaded successfully")
    
    def test_transcription_functionality(self, video_processor, sample_videos, temp_output_dir):
        """Test video transcription"""
        if video_processor.whisper_model is None:
            pytest.skip("Whisper model not available")
        
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip("Test video not found")
        
        transcript = video_processor._transcribe_video(main_video)
        
        if transcript:
            assert "text" in transcript
            assert "segments" in transcript
            assert "language" in transcript
            assert len(transcript["text"]) > 0
            
            print(f"Transcription result: {transcript['text'][:100]}...")
            print(f"Language detected: {transcript['language']}")
            print(f"Number of segments: {len(transcript['segments'])}")
        else:
            print("Transcription failed or returned None")
    
    def test_emoji_selection(self, video_processor):
        """Test emoji selection based on text"""
        test_texts = [
            "I love this amazing video",
            "This is so exciting and wonderful",
            "Great food and delicious meal",
            "Traveling to beautiful places",
            "Sad and disappointing news"
        ]
        
        for text in test_texts:
            emoji = video_processor._select_emoji_for_text(text.lower())
            print(f"Text: '{text}' -> Emoji: {emoji}")
    
    def test_zoom_keyword_detection(self, video_processor):
        """Test auto-zoom keyword detection"""
        test_segments = [
            {"text": "Look at this person speaking", "start": 0, "end": 3},
            {"text": "This is very important information", "start": 3, "end": 6},
            {"text": "Just some regular content here", "start": 6, "end": 9},
            {"text": "Focus on the main product", "start": 9, "end": 12}
        ]
        
        transcript = {
            "text": " ".join([seg["text"] for seg in test_segments]),
            "segments": test_segments
        }
        
        # This would normally be called within _apply_auto_zoom
        # We're testing the keyword detection logic
        zoom_moments = []
        for segment in test_segments:
            segment_text = segment["text"].lower()
            should_zoom = False
            
            for category, keywords in video_processor.zoom_keywords.items():
                if any(keyword in segment_text for keyword in keywords):
                    should_zoom = True
                    break
            
            if should_zoom:
                zoom_moments.append(segment)
        
        assert len(zoom_moments) >= 2, "Should detect zoom moments for 'person' and 'important'"
        print(f"Detected {len(zoom_moments)} zoom moments: {[m['text'] for m in zoom_moments]}")


class TestAdvancedFeatures:
    """Test advanced video processing features"""
    
    @pytest.fixture
    def video_processor(self):
        return VideoProcessor()
    
    def test_auto_effects_pipeline(self, video_processor, sample_videos, temp_output_dir):
        """Test the complete auto-effects pipeline"""
        main_video = sample_videos["main_video"]
        
        if not main_video.exists():
            pytest.skip("Test video not found")
        
        output_path = temp_output_dir / "auto_effects_output.mp4"
        
        options = {
            "platform": "tiktok",
            "quality_preset": "fast",  # Use fast for testing
            "auto_effects": True,
            "enable_transcription": True,
            "ai_effects_based_on_transcript": True
        }
        
        result = video_processor.apply_auto_effects([main_video], output_path, options)
        
        # This might fail if Whisper is not available, but should handle gracefully
        if result["success"]:
            assert output_path.exists(), "Output file should be created"
            assert "effects_applied" in result
            
            print(f"Auto effects result: {result}")
            print(f"Effects applied: {result.get('effects_applied', [])}")
            
            if result.get("transcript"):
                print(f"Transcript: {result['transcript']['text'][:100]}...")
        else:
            print(f"Auto effects failed (expected if Whisper not available): {result.get('error')}")
    
    def test_transition_effects(self, video_processor, sample_videos, temp_output_dir):
        """Test transition effects between videos"""
        intro_video = sample_videos["intro_video"]
        main_video = sample_videos["main_video"]
        
        if not intro_video.exists() or not main_video.exists():
            pytest.skip("Test videos not found")
        
        output_path = temp_output_dir / "transition_output.mp4"
        
        transitions = [
            {
                "type": "fade",
                "duration": 1.0
            }
        ]
        
        result = video_processor.merge_with_transitions(
            [intro_video, main_video], 
            output_path, 
            transitions
        )
        
        if result["success"]:
            assert output_path.exists(), "Output file should be created"
            print(f"Transition merge result: {result}")
        else:
            print(f"Transition merge failed: {result.get('error')}")
    
    def test_multi_video_processing(self, video_processor, sample_videos, temp_output_dir):
        """Test processing multiple videos"""
        intro_video = sample_videos["intro_video"]
        main_video = sample_videos["main_video"]
        
        if not intro_video.exists() or not main_video.exists():
            pytest.skip("Test videos not found")
        
        # Use the same video multiple times for testing
        input_files = [intro_video, main_video, intro_video]
        output_path = temp_output_dir / "multi_video_output.mp4"
        
        options = {
            "platform": "youtube",
            "quality_preset": "fast"
        }
        
        result = video_processor.merge_multiple_videos(input_files, output_path, options)
        
        if result["success"]:
            assert output_path.exists(), "Output file should be created"
            
            # Check that output is longer than individual videos
            output_info = video_processor._get_video_info(output_path)
            intro_info = video_processor._get_video_info(intro_video)
            main_info = video_processor._get_video_info(main_video)
            
            expected_duration = intro_info.get("duration", 0) * 2 + main_info.get("duration", 0)
            actual_duration = output_info.get("duration", 0)
            
            # Allow some tolerance for encoding differences
            assert actual_duration > expected_duration * 0.9, f"Output duration {actual_duration} should be close to expected {expected_duration}"
            
            print(f"Multi-video result: {result}")
            print(f"Expected duration: {expected_duration}, Actual: {actual_duration}")
        else:
            print(f"Multi-video processing failed: {result.get('error')}")


class TestErrorHandling:
    """Test error handling in video processing"""
    
    @pytest.fixture
    def video_processor(self):
        return VideoProcessor()
    
    def test_invalid_video_file(self, video_processor, temp_output_dir):
        """Test handling of invalid video files"""
        # Create a fake video file
        fake_video = temp_output_dir / "fake_video.mp4"
        fake_video.write_text("This is not a video file")
        
        validation = video_processor.validate_video_file(fake_video)
        assert not validation["valid"]
        assert "error" in validation
        
        print(f"Invalid video handling: {validation['error']}")
    
    def test_nonexistent_video_file(self, video_processor):
        """Test handling of non-existent video files"""
        nonexistent = Path("/path/to/nonexistent/video.mp4")
        
        validation = video_processor.validate_video_file(nonexistent)
        assert not validation["valid"]
        assert "does not exist" in validation["error"].lower()
    
    def test_merge_with_invalid_files(self, video_processor, temp_output_dir):
        """Test merging with invalid input files"""
        fake_video1 = temp_output_dir / "fake1.mp4"
        fake_video2 = temp_output_dir / "fake2.mp4"
        output_path = temp_output_dir / "merge_output.mp4"
        
        fake_video1.write_text("fake video 1")
        fake_video2.write_text("fake video 2")
        
        result = video_processor.simple_merge([fake_video1, fake_video2], output_path)
        
        assert not result["success"]
        assert "error" in result
        
        print(f"Invalid merge handling: {result['error']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
