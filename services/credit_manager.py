"""
Credit management service for video processing API
"""
import math
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from models.schemas import JobType, TransactionType
# Import database service based on configuration
from config.settings import settings
if settings.USE_SQLITE:
    from services.database_sqlite import SQLiteDatabaseService as DatabaseService
else:
    from services.database import DatabaseService
from config.settings import CREDIT_COSTS, settings

logger = logging.getLogger(__name__)

class CreditManager:
    """Manages credit calculations, validation, and transactions"""
    
    def __init__(self, db_service=None):
        self.db_service = db_service if db_service else DatabaseService()
    
    def calculate_credits_for_job(
        self, 
        job_type: JobType, 
        videos: List[Dict[str, Any]], 
        processing_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate total credits required for a job
        """
        try:
            # Get base costs for job type
            job_costs = CREDIT_COSTS.get(job_type.value, {})
            base_cost = job_costs.get('base_cost', 0)
            per_10_seconds_cost = job_costs.get('per_10_seconds', 0)
            
            # Calculate total duration
            total_duration = sum(video.get('duration', 0) for video in videos)
            duration_segments = math.ceil(total_duration / 10.0)  # Round up to nearest 10 seconds
            
            # Base calculation
            duration_credits = duration_segments * per_10_seconds_cost
            total_credits = base_cost + duration_credits
            
            breakdown = {
                'base_cost': base_cost,
                'duration_credits': duration_credits,
                'total_duration_seconds': total_duration
            }
            
            # Add costs for specific features
            if job_type == JobType.MULTI_VIDEO:
                additional_videos = max(0, len(videos) - 2)  # First 2 videos included in base
                additional_cost = additional_videos * job_costs.get('per_additional_video', 1)
                total_credits += additional_cost
                breakdown['additional_videos_cost'] = additional_cost
            
            # Transition costs
            if processing_options.get('transitions'):
                transition_cost = self._calculate_transition_costs(processing_options['transitions'])
                total_credits += transition_cost
                breakdown['transition_cost'] = transition_cost
            
            # Auto-effects costs
            if processing_options.get('auto_effects'):
                effects_cost = self._calculate_auto_effects_costs(total_duration, processing_options)
                total_credits += effects_cost
                breakdown['auto_effects_cost'] = effects_cost
            
            # Transcription costs
            if processing_options.get('enable_transcription'):
                transcription_cost = self._calculate_transcription_costs(total_duration)
                total_credits += transcription_cost
                breakdown['transcription_cost'] = transcription_cost
            
            # Logo overlay costs
            if processing_options.get('logo_overlay'):
                logo_cost = self._calculate_logo_overlay_costs(total_duration)
                total_credits += logo_cost
                breakdown['logo_overlay_cost'] = logo_cost

            # Premium AI enhancement costs
            if job_type == JobType.PREMIUM_AI_ENHANCEMENT:
                premium_cost = self._calculate_premium_ai_costs(total_duration, processing_options)
                total_credits += premium_cost
                breakdown['premium_ai_cost'] = premium_cost
            
            # Quality preset multiplier
            quality_preset = processing_options.get('quality_preset', 'balanced')
            quality_multipliers = {'fast': 0.8, 'balanced': 1.0, 'quality': 1.3}
            quality_multiplier = quality_multipliers.get(quality_preset, 1.0)
            
            if quality_multiplier != 1.0:
                quality_adjustment = int((total_credits * quality_multiplier) - total_credits)
                total_credits = int(total_credits * quality_multiplier)
                breakdown['quality_adjustment'] = quality_adjustment
            
            return {
                'total_credits': max(0, total_credits),  # Ensure non-negative
                'breakdown': breakdown,
                'total_duration_seconds': total_duration
            }
            
        except Exception as e:
            logger.error(f"Error calculating credits: {str(e)}")
            # Return a safe default
            return {
                'total_credits': 10,  # Conservative estimate
                'breakdown': {'error': str(e)},
                'total_duration_seconds': 0
            }
    
    def _calculate_transition_costs(self, transitions: List[Dict[str, Any]]) -> int:
        """Calculate costs for transition effects"""
        total_cost = 0
        
        for transition in transitions:
            transition_type = transition.get('type', 'fade')
            transition_costs = CREDIT_COSTS.get('custom_transitions', {})
            
            base_cost = transition_costs.get('base_cost', 3)
            per_transition = transition_costs.get('per_transition', 2)
            
            # Custom transitions cost more
            if transition_type == 'custom':
                total_cost += base_cost + (per_transition * 2)
            else:
                total_cost += per_transition
        
        return total_cost
    
    def _calculate_auto_effects_costs(self, duration: float, options: Dict[str, Any]) -> int:
        """Calculate costs for auto-effects"""
        auto_effects_costs = CREDIT_COSTS.get('auto_effects', {})
        base_cost = auto_effects_costs.get('base_cost', 5)
        per_10_seconds = auto_effects_costs.get('per_10_seconds', 2)
        
        duration_segments = math.ceil(duration / 10.0)
        return base_cost + (duration_segments * per_10_seconds)
    
    def _calculate_transcription_costs(self, duration: float) -> int:
        """Calculate costs for transcription services"""
        # Transcription typically costs per minute
        minutes = math.ceil(duration / 60.0)
        cost_per_minute = 1  # 1 credit per minute
        return minutes * cost_per_minute
    
    def _calculate_logo_overlay_costs(self, duration: float) -> int:
        """Calculate costs for logo overlay"""
        logo_costs = CREDIT_COSTS.get('logo_overlay', {})
        base_cost = logo_costs.get('base_cost', 2)
        per_10_seconds = logo_costs.get('per_10_seconds', 1)

        duration_segments = math.ceil(duration / 10.0)
        return base_cost + (duration_segments * per_10_seconds)

    def _calculate_premium_ai_costs(self, duration: float, options: Dict[str, Any]) -> int:
        """Calculate costs for premium AI enhancement"""
        # Premium AI enhancement: 100 credits per minute base
        minutes = math.ceil(duration / 60.0)
        base_cost_per_minute = 100
        base_cost = minutes * base_cost_per_minute

        # Additional costs for specific AI features
        additional_cost = 0

        # AI smart zoom
        if options.get('ai_smart_zoom'):
            additional_cost += minutes * 20  # 20 credits per minute

        # AI smart captions
        if options.get('ai_smart_captions'):
            additional_cost += minutes * 15  # 15 credits per minute

        # AI smart overlays
        if options.get('ai_smart_overlays'):
            additional_cost += minutes * 10  # 10 credits per minute

        # AI smart transitions
        if options.get('ai_smart_transitions'):
            additional_cost += minutes * 10  # 10 credits per minute

        # Premium logo overlay (higher quality)
        if options.get('premium_logo_overlay'):
            additional_cost += minutes * 5  # 5 credits per minute

        # Effect intensity multiplier
        intensity_preference = options.get('effect_intensity_preference', 'balanced')
        intensity_multipliers = {
            'subtle': 0.8,
            'balanced': 1.0,
            'dramatic': 1.3
        }
        intensity_multiplier = intensity_multipliers.get(intensity_preference, 1.0)

        # Max effects per minute multiplier
        max_effects = options.get('max_effects_per_minute', 5)
        effects_multiplier = 1.0 + (max_effects - 5) * 0.1  # 10% more per effect above 5

        total_cost = int((base_cost + additional_cost) * intensity_multiplier * effects_multiplier)

        # Minimum cost for premium processing
        minimum_cost = 50
        return max(total_cost, minimum_cost)
    
    def has_sufficient_credits(self, user_id: UUID, required_credits: int) -> bool:
        """Check if user has sufficient credits"""
        try:
            user_credits = self.db_service.get_user_credits(user_id)
            if not user_credits:
                return False
            
            remaining_credits = user_credits.get('remaining_credits', 0)
            return remaining_credits >= required_credits
            
        except Exception as e:
            logger.error(f"Error checking user credits: {str(e)}")
            return False
    
    def reserve_credits(self, user_id: UUID, amount: int, job_id: UUID) -> bool:
        """Reserve credits for a job (temporary hold)"""
        try:
            # Create a pending transaction
            transaction_data = {
                'user_id': user_id,
                'transaction_type': TransactionType.USAGE,
                'amount': -amount,  # Negative for usage
                'description': f'Reserved for job {job_id}',
                'job_id': job_id
            }
            
            # Check if user has sufficient credits before reserving
            if not self.has_sufficient_credits(user_id, amount):
                return False
            
            # Create the transaction (this will be finalized later)
            transaction_id = self.db_service.create_credit_transaction(transaction_data)
            
            # Update user's used credits
            self.db_service.update_user_credits_usage(user_id, amount)
            
            logger.info(f"Reserved {amount} credits for user {user_id}, job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reserving credits: {str(e)}")
            return False
    
    def finalize_credits(self, user_id: UUID, reserved_amount: int, actual_amount: int, job_id: UUID) -> bool:
        """Finalize credit usage after job completion"""
        try:
            # If actual usage is less than reserved, refund the difference
            if actual_amount < reserved_amount:
                refund_amount = reserved_amount - actual_amount
                self.refund_credits(user_id, refund_amount, job_id, "Unused reserved credits")
            
            # Update the transaction description
            self.db_service.update_credit_transaction_description(
                job_id, 
                f'Final usage for completed job {job_id} - {actual_amount} credits'
            )
            
            logger.info(f"Finalized {actual_amount} credits for user {user_id}, job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing credits: {str(e)}")
            return False
    
    def refund_credits(self, user_id: UUID, amount: int, job_id: UUID, reason: str = "Job failed") -> bool:
        """Refund credits to user"""
        try:
            # Create refund transaction
            transaction_data = {
                'user_id': user_id,
                'transaction_type': TransactionType.REFUND,
                'amount': amount,  # Positive for refund
                'description': f'Refund: {reason}',
                'job_id': job_id
            }
            
            transaction_id = self.db_service.create_credit_transaction(transaction_data)
            
            # Update user's used credits (reduce usage)
            self.db_service.update_user_credits_usage(user_id, -amount)
            
            logger.info(f"Refunded {amount} credits to user {user_id} for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error refunding credits: {str(e)}")
            return False
    
    def add_credits(self, user_id: UUID, amount: int, reason: str = "Purchase") -> bool:
        """Add credits to user account"""
        try:
            # Create purchase transaction
            transaction_data = {
                'user_id': user_id,
                'transaction_type': TransactionType.PURCHASE,
                'amount': amount,
                'description': reason,
                'job_id': None
            }
            
            transaction_id = self.db_service.create_credit_transaction(transaction_data)
            
            # Update user's total credits
            self.db_service.update_user_total_credits(user_id, amount)
            
            logger.info(f"Added {amount} credits to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding credits: {str(e)}")
            return False
    
    def get_user_credit_history(self, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's credit transaction history"""
        try:
            return self.db_service.get_user_credit_transactions(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting credit history: {str(e)}")
            return []
    
    def calculate_actual_credits(
        self, 
        job_type: JobType, 
        actual_duration: float, 
        processing_options: Dict[str, Any]
    ) -> int:
        """Calculate actual credits used based on final output"""
        # This is similar to calculate_credits_for_job but uses actual duration
        mock_videos = [{'duration': actual_duration}]
        result = self.calculate_credits_for_job(job_type, mock_videos, processing_options)
        return result['total_credits']
