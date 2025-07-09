"""
Premium Video Processing Celery Tasks

Handles AI-powered video enhancement with step-by-step progress tracking
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from uuid import UUID
import asyncio

from celery_app import celery_app
from services.database import get_database_service
from services.storage import get_storage_service
from services.credit_manager import CreditManager
from services.premium_video_processor import PremiumVideoProcessor, ProcessingStep
from models.job import JobStatus, JobType

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, queue="premium_processing")
def process_premium_video_job(self, job_config: Dict[str, Any]):
    """
    Process premium video with AI-powered effects
    
    Args:
        job_config: Job configuration including input paths and processing options
    """
    job_id = job_config['job_id']
    user_id = job_config['user_id']
    
    logger.info(f"Starting premium video processing for job {job_id}")
    
    try:
        # Initialize services
        db_service = get_database_service()
        storage_service = get_storage_service()
        credit_manager = CreditManager(db_service)
        processor = PremiumVideoProcessor()
        
        # Update job status
        db_service.update_job_status(UUID(job_id), JobStatus.PROCESSING)
        
        # Get input configuration
        input_config = job_config['input_config']
        processing_options = job_config['processing_options']
        estimated_credits = job_config['estimated_credits']
        
        video_path = Path(input_config['video_path'])
        logo_path = Path(input_config['logo_path']) if input_config.get('logo_path') else None
        
        # Create progress callback
        def progress_callback(progress):
            """Update job progress in database"""
            try:
                progress_data = {
                    'current_step': progress.current_step.value,
                    'completed_steps': [step.value for step in progress.completed_steps],
                    'failed_steps': [step.value for step in progress.failed_steps],
                    'progress_percentage': progress.progress_percentage,
                    'step_outputs': progress.step_outputs,
                    'retry_count': progress.retry_count,
                    'error_message': progress.error_message
                }
                
                db_service.update_job_progress(UUID(job_id), progress_data)
                
                # Update Celery task state
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress.progress_percentage,
                        'current_step': progress.current_step.value,
                        'completed_steps': len(progress.completed_steps),
                        'total_steps': len(ProcessingStep) - 1  # Exclude COMPLETED
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to update progress for job {job_id}: {e}")
        
        # Process video with premium effects
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                processor.process_premium_video(
                    video_path=video_path,
                    job_id=job_id,
                    logo_path=logo_path,
                    progress_callback=progress_callback
                )
            )
        finally:
            loop.close()
        
        if result.error_message:
            # Processing failed
            logger.error(f"Premium processing failed for job {job_id}: {result.error_message}")
            
            # Update job status
            db_service.update_job_status(UUID(job_id), JobStatus.FAILED, result.error_message)
            
            # Refund credits
            credit_manager.refund_credits(UUID(user_id), estimated_credits, UUID(job_id))
            
            return {
                'success': False,
                'job_id': job_id,
                'error': result.error_message,
                'progress': result
            }
        
        # Processing successful - upload final video
        final_video_path = result.step_outputs.get(ProcessingStep.FINAL_ASSEMBLY.value)
        if not final_video_path or not Path(final_video_path).exists():
            raise Exception("Final video file not found")
        
        # Upload to storage
        output_filename = f"premium_processed/{job_id}/final_video.mp4"
        output_url = storage_service.upload_to_storage(Path(final_video_path), output_filename)
        
        # Get video metadata
        video_size = Path(final_video_path).stat().st_size
        duration = input_config['duration_seconds']
        
        # Calculate actual credits used based on complexity
        actual_credits = result.estimated_credits or estimated_credits
        
        # Finalize credit transaction
        credit_manager.finalize_credits(
            UUID(user_id), 
            estimated_credits, 
            actual_credits, 
            UUID(job_id)
        )
        
        # Update job completion
        db_service.update_job_completion(
            UUID(job_id),
            JobStatus.COMPLETED,
            output_url,
            video_size,
            duration,
            actual_credits
        )
        
        # Save final progress
        final_progress = {
            'current_step': ProcessingStep.COMPLETED.value,
            'completed_steps': [step.value for step in result.completed_steps],
            'progress_percentage': 100.0,
            'step_outputs': result.step_outputs,
            'ai_analysis_summary': _extract_ai_summary(result),
            'effects_applied': _count_effects_applied(result)
        }
        
        db_service.update_job_progress(UUID(job_id), final_progress)
        
        logger.info(f"Premium processing completed successfully for job {job_id}")
        
        return {
            'success': True,
            'job_id': job_id,
            'output_url': output_url,
            'credits_used': actual_credits,
            'effects_applied': final_progress['effects_applied'],
            'processing_summary': final_progress
        }
        
    except Exception as e:
        logger.error(f"Premium processing failed for job {job_id}: {e}")
        
        # Update job status
        db_service.update_job_status(UUID(job_id), JobStatus.FAILED, str(e))
        
        # Refund credits
        credit_manager.refund_credits(UUID(user_id), estimated_credits, UUID(job_id))
        
        return {
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }

@celery_app.task(bind=True, queue="premium_processing")
def retry_premium_video_job(self, retry_config: Dict[str, Any]):
    """
    Retry a failed premium video processing job from a specific step
    
    Args:
        retry_config: Retry configuration including job_id and step to retry from
    """
    job_id = retry_config['job_id']
    retry_from_step = retry_config.get('retry_from_step')
    
    logger.info(f"Retrying premium video processing for job {job_id} from step {retry_from_step}")
    
    try:
        # Load original job configuration
        db_service = get_database_service()
        job = db_service.get_job(job_id)
        
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        # Reconstruct job config for retry
        job_config = {
            'job_id': job_id,
            'user_id': job['user_id'],
            'input_config': job['input_config'],
            'processing_options': job['processing_options'],
            'estimated_credits': job['estimated_credits'],
            'retry_from_step': retry_from_step
        }
        
        # Process with retry logic
        return process_premium_video_job.apply_async(args=[job_config])
        
    except Exception as e:
        logger.error(f"Premium processing retry failed for job {job_id}: {e}")
        
        # Update job status
        db_service.update_job_status(UUID(job_id), JobStatus.FAILED, f"Retry failed: {str(e)}")
        
        return {
            'success': False,
            'job_id': job_id,
            'error': f"Retry failed: {str(e)}"
        }

def _extract_ai_summary(processing_result) -> Dict[str, Any]:
    """Extract AI analysis summary from processing result"""
    try:
        ai_analysis_file = processing_result.step_outputs.get(ProcessingStep.AI_ANALYSIS.value)
        if ai_analysis_file and Path(ai_analysis_file).exists():
            with open(ai_analysis_file, 'r') as f:
                ai_data = json.load(f)
                
            return {
                'total_effects_detected': ai_data.get('total_effects', 0),
                'complexity': ai_data.get('processing_complexity', 'unknown'),
                'zoom_moments': len(ai_data.get('zoom_moments', [])),
                'caption_moments': len(ai_data.get('caption_moments', [])),
                'overlay_moments': len(ai_data.get('overlay_moments', [])),
                'ai_confidence': _calculate_average_confidence(ai_data)
            }
    except Exception as e:
        logger.warning(f"Failed to extract AI summary: {e}")
    
    return {'error': 'AI summary not available'}

def _count_effects_applied(processing_result) -> Dict[str, int]:
    """Count the number of effects actually applied"""
    effects_count = {
        'zoom_effects': 0,
        'caption_effects': 0,
        'overlay_effects': 0,
        'logo_overlay': 0
    }
    
    try:
        # Check which steps were completed
        completed_steps = [step.value for step in processing_result.completed_steps]
        
        if ProcessingStep.ZOOM_EFFECTS.value in completed_steps:
            effects_count['zoom_effects'] = 1  # Could be enhanced to count actual effects
        
        if ProcessingStep.CAPTION_EFFECTS.value in completed_steps:
            effects_count['caption_effects'] = 1
        
        if ProcessingStep.OVERLAY_EFFECTS.value in completed_steps:
            effects_count['overlay_effects'] = 1
        
        if ProcessingStep.LOGO_OVERLAY.value in completed_steps:
            effects_count['logo_overlay'] = 1
            
    except Exception as e:
        logger.warning(f"Failed to count effects: {e}")
    
    return effects_count

def _calculate_average_confidence(ai_data: Dict[str, Any]) -> float:
    """Calculate average confidence from AI analysis"""
    try:
        all_effects = []
        all_effects.extend(ai_data.get('zoom_moments', []))
        all_effects.extend(ai_data.get('caption_moments', []))
        all_effects.extend(ai_data.get('overlay_moments', []))
        
        if not all_effects:
            return 0.0
        
        total_confidence = sum(effect.get('confidence', 0.0) for effect in all_effects)
        return total_confidence / len(all_effects)
        
    except Exception:
        return 0.0
