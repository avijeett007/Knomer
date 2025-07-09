"""
Tests for the credit management system
"""
import pytest
from uuid import UUID
from services.credit_manager import CreditManager
from models.schemas import JobType, TransactionType

class TestCreditCalculation:
    """Test credit calculation logic"""
    
    def test_simple_merge_free(self, credit_manager):
        """Test that simple merge is free"""
        videos = [
            {"duration": 30.0},  # 30 seconds
            {"duration": 45.0}   # 45 seconds
        ]
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced"
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.SIMPLE_MERGE,
            videos,
            processing_options
        )
        
        assert result["total_credits"] == 0
        assert result["breakdown"]["base_cost"] == 0
        assert result["breakdown"]["duration_credits"] == 0
        
    def test_transition_merge_credits(self, credit_manager):
        """Test transition merge credit calculation"""
        videos = [
            {"duration": 20.0},  # 20 seconds = 2 segments
            {"duration": 30.0}   # 30 seconds = 3 segments
        ]
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced",
            "transitions": [
                {"type": "fade", "duration": 1.0}
            ]
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.TRANSITION_MERGE,
            videos,
            processing_options
        )
        
        # Should have base cost + duration cost + transition cost
        assert result["total_credits"] > 0
        assert "transition_cost" in result["breakdown"]
        
    def test_auto_effects_with_transcription(self, credit_manager):
        """Test auto effects with transcription costs"""
        videos = [{"duration": 60.0}]  # 1 minute = 6 segments
        
        processing_options = {
            "platform": "tiktok",
            "quality_preset": "balanced",
            "auto_effects": True,
            "enable_transcription": True,
            "ai_effects_based_on_transcript": True
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.AUTO_EFFECTS,
            videos,
            processing_options
        )
        
        assert result["total_credits"] > 10  # Should be significant
        assert "auto_effects_cost" in result["breakdown"]
        assert "transcription_cost" in result["breakdown"]
        
    def test_logo_overlay_credits(self, credit_manager):
        """Test logo overlay credit calculation"""
        videos = [{"duration": 40.0}]  # 40 seconds = 4 segments
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced",
            "logo_overlay": {
                "logo_url": "https://example.com/logo.png",
                "position": "top-right",
                "size": 0.15
            }
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.LOGO_OVERLAY,
            videos,
            processing_options
        )
        
        assert result["total_credits"] > 0
        assert "logo_overlay_cost" in result["breakdown"]
        
    def test_multi_video_additional_cost(self, credit_manager):
        """Test multi-video processing with additional video costs"""
        videos = [
            {"duration": 10.0},
            {"duration": 15.0},
            {"duration": 20.0},  # 3rd video should incur additional cost
            {"duration": 25.0}   # 4th video should incur additional cost
        ]
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced"
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.MULTI_VIDEO,
            videos,
            processing_options
        )
        
        assert result["total_credits"] > 0
        assert "additional_videos_cost" in result["breakdown"]
        # Should charge for 2 additional videos (beyond the first 2)
        assert result["breakdown"]["additional_videos_cost"] == 2
        
    def test_quality_preset_multiplier(self, credit_manager):
        """Test quality preset affects credit calculation"""
        videos = [{"duration": 30.0}]
        
        # Test different quality presets
        base_options = {
            "platform": "youtube",
            "logo_overlay": {
                "logo_url": "https://example.com/logo.png",
                "position": "top-right"
            }
        }
        
        # Fast preset (0.8x multiplier)
        fast_options = {**base_options, "quality_preset": "fast"}
        fast_result = credit_manager.calculate_credits_for_job(
            JobType.LOGO_OVERLAY, videos, fast_options
        )
        
        # Quality preset (1.3x multiplier)
        quality_options = {**base_options, "quality_preset": "quality"}
        quality_result = credit_manager.calculate_credits_for_job(
            JobType.LOGO_OVERLAY, videos, quality_options
        )
        
        # Quality preset should cost more than fast
        assert quality_result["total_credits"] > fast_result["total_credits"]


class TestCreditTransactions:
    """Test credit transaction operations"""
    
    @pytest.mark.asyncio
    async def test_credit_reservation_and_finalization(
        self, 
        credit_manager, 
        test_user, 
        test_credits
    ):
        """Test credit reservation and finalization flow"""
        user_id = UUID(test_user["user_id"])
        job_id = UUID("12345678-1234-1234-1234-123456789012")
        
        # Check initial credits
        initial_credits = credit_manager.db_service.get_user_credits(user_id)
        initial_remaining = initial_credits["remaining_credits"]
        
        # Reserve credits
        reserve_amount = 50
        success = credit_manager.reserve_credits(user_id, reserve_amount, job_id)
        assert success, "Credit reservation should succeed"
        
        # Check credits after reservation
        after_reserve = credit_manager.db_service.get_user_credits(user_id)
        assert after_reserve["remaining_credits"] == initial_remaining - reserve_amount
        
        # Finalize with actual usage (less than reserved)
        actual_amount = 30
        success = credit_manager.finalize_credits(
            user_id, reserve_amount, actual_amount, job_id
        )
        assert success, "Credit finalization should succeed"
        
        # Check final credits (should have refund for unused credits)
        final_credits = credit_manager.db_service.get_user_credits(user_id)
        assert final_credits["remaining_credits"] == initial_remaining - actual_amount
        
    @pytest.mark.asyncio
    async def test_credit_refund(self, credit_manager, test_user, test_credits):
        """Test credit refund functionality"""
        user_id = UUID(test_user["user_id"])
        job_id = UUID("12345678-1234-1234-1234-123456789013")
        
        # Get initial credits
        initial_credits = credit_manager.db_service.get_user_credits(user_id)
        initial_remaining = initial_credits["remaining_credits"]
        
        # Reserve credits
        reserve_amount = 40
        credit_manager.reserve_credits(user_id, reserve_amount, job_id)
        
        # Refund all credits (job failed)
        success = credit_manager.refund_credits(
            user_id, reserve_amount, job_id, "Job processing failed"
        )
        assert success, "Credit refund should succeed"
        
        # Check credits are fully refunded
        final_credits = credit_manager.db_service.get_user_credits(user_id)
        assert final_credits["remaining_credits"] == initial_remaining
        
    @pytest.mark.asyncio
    async def test_insufficient_credits_check(self, credit_manager, test_user):
        """Test insufficient credits detection"""
        user_id = UUID(test_user["user_id"])
        
        # Get current credits
        current_credits = credit_manager.db_service.get_user_credits(user_id)
        remaining = current_credits["remaining_credits"]
        
        # Should have sufficient credits for amount less than remaining
        assert credit_manager.has_sufficient_credits(user_id, remaining - 1)
        
        # Should not have sufficient credits for amount greater than remaining
        assert not credit_manager.has_sufficient_credits(user_id, remaining + 1)
        
    @pytest.mark.asyncio
    async def test_add_credits(self, credit_manager, test_user):
        """Test adding credits to user account"""
        user_id = UUID(test_user["user_id"])
        
        # Get initial credits
        initial_credits = credit_manager.db_service.get_user_credits(user_id)
        initial_total = initial_credits["total_credits"]
        
        # Add credits
        add_amount = 500
        success = credit_manager.add_credits(
            user_id, add_amount, "Test credit purchase"
        )
        assert success, "Adding credits should succeed"
        
        # Check credits were added
        final_credits = credit_manager.db_service.get_user_credits(user_id)
        assert final_credits["total_credits"] == initial_total + add_amount
        
    @pytest.mark.asyncio
    async def test_credit_transaction_history(self, credit_manager, test_user):
        """Test credit transaction history tracking"""
        user_id = UUID(test_user["user_id"])
        job_id = UUID("12345678-1234-1234-1234-123456789014")
        
        # Perform several credit operations
        credit_manager.add_credits(user_id, 100, "Test purchase")
        credit_manager.reserve_credits(user_id, 50, job_id)
        credit_manager.finalize_credits(user_id, 50, 30, job_id)
        
        # Get transaction history
        history = credit_manager.get_user_credit_history(user_id, limit=10)
        
        assert len(history) >= 3, "Should have at least 3 transactions"
        
        # Check transaction types are recorded
        transaction_types = [tx.get("transaction_type") for tx in history]
        assert TransactionType.PURCHASE.value in transaction_types
        assert TransactionType.USAGE.value in transaction_types


class TestCreditEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_zero_duration_video(self, credit_manager):
        """Test handling of zero duration videos"""
        videos = [{"duration": 0.0}]
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced"
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.SIMPLE_MERGE,
            videos,
            processing_options
        )
        
        # Should handle gracefully
        assert result["total_credits"] >= 0
        assert result["total_duration_seconds"] == 0.0
        
    def test_very_long_video(self, credit_manager):
        """Test handling of very long videos"""
        videos = [{"duration": 3600.0}]  # 1 hour
        
        processing_options = {
            "platform": "youtube",
            "quality_preset": "balanced",
            "auto_effects": True,
            "enable_transcription": True
        }
        
        result = credit_manager.calculate_credits_for_job(
            JobType.AUTO_EFFECTS,
            videos,
            processing_options
        )
        
        # Should calculate credits for long video
        assert result["total_credits"] > 100  # Should be expensive
        assert result["total_duration_seconds"] == 3600.0
        
    def test_invalid_job_type(self, credit_manager):
        """Test handling of invalid job type"""
        videos = [{"duration": 30.0}]
        processing_options = {"platform": "youtube"}
        
        # This should not crash, but return a safe default
        result = credit_manager.calculate_credits_for_job(
            "invalid_job_type",  # Invalid job type
            videos,
            processing_options
        )
        
        # Should return some default credits
        assert "total_credits" in result
        assert result["total_credits"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
