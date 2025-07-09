"""
End-to-End tests for video processing functionality
"""
import pytest
import time
import json
from pathlib import Path
from uuid import UUID

# Test data generators from conftest
from conftest import (
    generate_simple_merge_job,
    generate_transition_merge_job,
    generate_auto_effects_job,
    generate_logo_overlay_job
)

class TestSimpleVideoMerge:
    """Test basic video merging functionality"""
    
    @pytest.mark.asyncio
    async def test_simple_merge_two_videos(
        self, 
        api_helper, 
        sample_videos, 
        storage_service, 
        test_credits,
        temp_dir
    ):
        """Test merging two videos without transitions"""
        # Upload test videos to storage
        main_video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/main_video.mp4"
        )
        intro_video_url = storage_service.upload_to_storage(
            sample_videos["intro_video"], 
            "test/intro_video.mp4"
        )
        
        assert main_video_url, "Failed to upload main video"
        assert intro_video_url, "Failed to upload intro video"
        
        # Create job
        job_data = generate_simple_merge_job([intro_video_url, main_video_url])
        
        # Estimate credits first
        estimation_data = {
            "job_type": "simple_merge",
            "videos": job_data["videos"],
            "processing_options": job_data["processing_options"]
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200, f"Credit estimation failed: {credits_response}"
        assert credits_response["estimated_credits"] == 0, "Simple merge should be free"
        
        # Create the job
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200, f"Job creation failed: {job_response}"
        
        job_id = job_response["id"]
        assert job_id, "Job ID not returned"
        
        # Wait for completion
        final_status = api_helper.wait_for_job_completion(job_id)
        assert "error" not in final_status, f"Job failed: {final_status}"
        
        job_info = final_status["job"]
        assert job_info["status"] == "completed", f"Job not completed: {job_info['status']}"
        assert job_info["output_file_url"], "No output file URL"
        assert job_info["actual_credits_used"] == 0, "Simple merge should use 0 credits"
        
        # Verify output file exists and is valid
        output_url = job_info["output_file_url"]
        assert output_url.startswith("http"), "Invalid output URL"
        
        print(f"✅ Simple merge completed successfully: {output_url}")

    @pytest.mark.asyncio
    async def test_simple_merge_credit_calculation(
        self,
        api_helper,
        sample_videos,
        storage_service
    ):
        """Test that simple merge is free regardless of video length"""
        # Upload test video
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/credit_test_video.mp4"
        )
        
        # Create estimation request
        estimation_data = {
            "job_type": "simple_merge",
            "videos": [
                {"url": video_url, "order_index": 0},
                {"url": video_url, "order_index": 1}  # Same video twice
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "balanced"
            }
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200
        assert credits_response["estimated_credits"] == 0
        
        print("✅ Simple merge credit calculation verified as free")


class TestTransitionEffects:
    """Test video transitions and effects"""
    
    @pytest.mark.asyncio
    async def test_fade_transition(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test fade transition between videos"""
        # Upload videos
        video1_url = storage_service.upload_to_storage(
            sample_videos["intro_video"],
            "test/transition_video1.mp4"
        )
        video2_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/transition_video2.mp4"
        )
        
        # Define transitions
        transitions = [
            {
                "type": "fade",
                "duration": 1.5
            }
        ]
        
        job_data = generate_transition_merge_job([video1_url, video2_url], transitions)
        
        # Estimate credits
        estimation_data = {
            "job_type": "transition_merge",
            "videos": job_data["videos"],
            "processing_options": job_data["processing_options"]
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200
        estimated_credits = credits_response["estimated_credits"]
        assert estimated_credits > 0, "Transition merge should cost credits"
        
        # Create job
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        
        # Wait for completion
        final_status = api_helper.wait_for_job_completion(job_id)
        assert "error" not in final_status
        
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        assert job_info["output_file_url"]
        
        print(f"✅ Fade transition completed: {job_info['output_file_url']}")

    @pytest.mark.asyncio
    async def test_custom_transition_clip(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test using custom transition clip"""
        # Upload videos and transition
        video1_url = storage_service.upload_to_storage(
            sample_videos["intro_video"],
            "test/custom_trans_video1.mp4"
        )
        video2_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/custom_trans_video2.mp4"
        )
        transition_url = storage_service.upload_to_storage(
            sample_videos["transition_video"],
            "test/custom_transition.mp4"
        )
        
        transitions = [
            {
                "type": "custom",
                "duration": 2.0,
                "custom_clip_url": transition_url
            }
        ]
        
        job_data = generate_transition_merge_job([video1_url, video2_url], transitions)
        
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id)
        
        assert "error" not in final_status
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        
        print(f"✅ Custom transition completed: {job_info['output_file_url']}")


class TestAutoEffects:
    """Test AI-powered auto effects"""
    
    @pytest.mark.asyncio
    async def test_auto_zoom_with_transcription(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test auto-zoom effects based on transcription"""
        # Upload video with speech
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/auto_zoom_video.mp4"
        )
        
        job_data = generate_auto_effects_job([video_url])
        
        # Estimate credits (should include transcription cost)
        estimation_data = {
            "job_type": "auto_effects",
            "videos": job_data["videos"],
            "processing_options": job_data["processing_options"]
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200
        estimated_credits = credits_response["estimated_credits"]
        assert estimated_credits > 5, "Auto effects should cost significant credits"
        
        # Create job
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id, timeout=600)  # Longer timeout for AI processing
        
        assert "error" not in final_status
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        assert job_info["output_file_url"]
        
        print(f"✅ Auto-zoom with transcription completed: {job_info['output_file_url']}")

    @pytest.mark.asyncio
    async def test_tiktok_resize_with_effects(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test TikTok-style resize with auto effects"""
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/tiktok_resize_video.mp4"
        )
        
        job_data = {
            "job_type": "auto_effects",
            "videos": [{"url": video_url, "order_index": 0}],
            "processing_options": {
                "platform": "tiktok",  # This should trigger 9:16 resize
                "quality_preset": "balanced",
                "auto_effects": True,
                "enable_transcription": True,
                "ai_effects_based_on_transcript": True
            }
        }
        
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id, timeout=600)
        
        assert "error" not in final_status
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        
        print(f"✅ TikTok resize with effects completed: {job_info['output_file_url']}")


class TestLogoOverlay:
    """Test logo watermarking functionality"""
    
    @pytest.mark.asyncio
    async def test_logo_overlay_top_right(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test logo overlay in top-right position"""
        # Upload video and logo
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/logo_overlay_video.mp4"
        )
        logo_url = storage_service.upload_to_storage(
            sample_videos["logo"],
            "test/logo.png"
        )
        
        job_data = generate_logo_overlay_job([video_url], logo_url)
        
        # Estimate credits
        estimation_data = {
            "job_type": "logo_overlay",
            "videos": job_data["videos"],
            "processing_options": job_data["processing_options"]
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200
        estimated_credits = credits_response["estimated_credits"]
        assert estimated_credits > 0, "Logo overlay should cost credits"
        
        # Create job
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id)
        
        assert "error" not in final_status
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        assert job_info["output_file_url"]
        
        print(f"✅ Logo overlay completed: {job_info['output_file_url']}")

    @pytest.mark.asyncio
    async def test_logo_overlay_different_positions(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test logo overlay in different positions"""
        video_url = storage_service.upload_to_storage(
            sample_videos["intro_video"],
            "test/logo_positions_video.mp4"
        )
        logo_url = storage_service.upload_to_storage(
            sample_videos["logo"],
            "test/logo_positions.png"
        )
        
        positions = ["top-left", "bottom-right", "center"]
        
        for position in positions:
            job_data = {
                "job_type": "logo_overlay",
                "videos": [{"url": video_url, "order_index": 0}],
                "processing_options": {
                    "platform": "youtube",
                    "quality_preset": "fast",  # Use fast for testing
                    "logo_overlay": {
                        "logo_url": logo_url,
                        "position": position,
                        "size": 0.12,
                        "opacity": 0.9
                    }
                }
            }
            
            job_response, status_code = api_helper.create_job(job_data)
            assert status_code == 200
            
            job_id = job_response["id"]
            final_status = api_helper.wait_for_job_completion(job_id)
            
            assert "error" not in final_status
            job_info = final_status["job"]
            assert job_info["status"] == "completed"
            
            print(f"✅ Logo overlay {position} completed: {job_info['output_file_url']}")


class TestMultiVideoProcessing:
    """Test processing multiple videos"""
    
    @pytest.mark.asyncio
    async def test_multi_video_merge_with_credits(
        self,
        api_helper,
        sample_videos,
        storage_service,
        test_credits
    ):
        """Test merging multiple videos with proper credit calculation"""
        # Upload multiple videos
        video_urls = []
        for i, video_key in enumerate(["intro_video", "main_video", "intro_video"]):  # 3 videos
            url = storage_service.upload_to_storage(
                sample_videos[video_key],
                f"test/multi_video_{i}.mp4"
            )
            video_urls.append(url)
        
        job_data = {
            "job_type": "multi_video",
            "videos": [
                {"url": url, "order_index": i}
                for i, url in enumerate(video_urls)
            ],
            "processing_options": {
                "platform": "youtube",
                "quality_preset": "balanced"
            }
        }
        
        # Estimate credits (should account for multiple videos)
        estimation_data = {
            "job_type": "multi_video",
            "videos": job_data["videos"],
            "processing_options": job_data["processing_options"]
        }
        
        credits_response, status_code = api_helper.estimate_credits(estimation_data)
        assert status_code == 200
        estimated_credits = credits_response["estimated_credits"]
        assert estimated_credits > 0, "Multi-video should cost credits for additional videos"
        
        # Create job
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id)
        
        assert "error" not in final_status
        job_info = final_status["job"]
        assert job_info["status"] == "completed"
        assert job_info["output_file_url"]
        
        print(f"✅ Multi-video merge completed: {job_info['output_file_url']}")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_video_url(self, api_helper):
        """Test handling of invalid video URLs"""
        job_data = generate_simple_merge_job([
            "https://invalid-url.com/nonexistent.mp4",
            "https://another-invalid-url.com/fake.mp4"
        ])
        
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 200  # Job should be created
        
        job_id = job_response["id"]
        final_status = api_helper.wait_for_job_completion(job_id)
        
        # Job should fail gracefully
        job_info = final_status["job"]
        assert job_info["status"] == "failed"
        assert job_info["error_message"]
        
        print(f"✅ Invalid URL handling verified: {job_info['error_message']}")

    @pytest.mark.asyncio
    async def test_insufficient_credits(
        self,
        api_helper,
        sample_videos,
        storage_service,
        credit_manager,
        test_user
    ):
        """Test handling of insufficient credits"""
        # Reduce user credits to very low amount
        user_id = UUID(test_user["user_id"])
        
        # Get current credits
        current_credits = credit_manager.db_service.get_user_credits(user_id)
        used_credits = current_credits["used_credits"]
        total_credits = current_credits["total_credits"]
        
        # Set used credits to almost total (leaving only 1 credit)
        credit_manager.db_service.update_user_credits_usage(
            user_id, 
            total_credits - used_credits - 1
        )
        
        # Try to create an expensive job
        video_url = storage_service.upload_to_storage(
            sample_videos["main_video"],
            "test/insufficient_credits_video.mp4"
        )
        
        job_data = generate_auto_effects_job([video_url])  # This should cost more than 1 credit
        
        job_response, status_code = api_helper.create_job(job_data)
        assert status_code == 402, "Should return 402 Payment Required for insufficient credits"
        assert "insufficient" in job_response.get("detail", "").lower()
        
        print("✅ Insufficient credits handling verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
