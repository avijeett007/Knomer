"""
Celery tasks for video processing
"""
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from celery import current_task
from celery_app import celery_app, PRIORITY_HIGH, PRIORITY_NORMAL
from models.schemas import JobStatus, JobType
from services.database import DatabaseService
from services.storage import StorageService
from services.credit_manager import CreditManager
from services.video_processor import VideoProcessor
from services.premium_video_processor import PremiumVideoProcessor
from services.audio_separator import AudioSeparator
from config.settings import settings

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, queue="video_processing")
def process_video_job(self, job_id: str, user_id: str) -> Dict[str, Any]:
    """
    Main task for processing video jobs
    """
    job_uuid = UUID(job_id)
    user_uuid = UUID(user_id)
    
    db_service = DatabaseService()
    storage_service = StorageService()
    credit_manager = CreditManager()
    video_processor = VideoProcessor()
    
    try:
        # Update job status to processing
        db_service.update_job_status(job_uuid, JobStatus.PROCESSING)
        
        # Get job details
        job = db_service.get_job(job_uuid)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Validate user credits
        estimated_credits = job.get('estimated_credits', 0)
        if not credit_manager.has_sufficient_credits(user_uuid, estimated_credits):
            raise ValueError("Insufficient credits")
        
        # Reserve credits
        credit_manager.reserve_credits(user_uuid, estimated_credits, job_uuid)
        
        # Download input videos
        input_files = []
        temp_dir = Path(tempfile.mkdtemp(prefix=f"job_{job_id}_"))
        
        try:
            for i, video_input in enumerate(job['input_config']['videos']):
                if video_input.get('url'):
                    # Download from external URL
                    file_path = temp_dir / f"input_{i}.mp4"
                    storage_service.download_file(video_input['url'], file_path)
                    input_files.append(file_path)
                else:
                    # File should be in our storage
                    file_path = temp_dir / f"input_{i}.mp4"
                    storage_service.download_from_storage(video_input['file_name'], file_path)
                    input_files.append(file_path)
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'progress': 20, 'status': 'Downloaded input files'}
            )
            
            # Process based on job type
            output_path = temp_dir / f"output_{job_id}.mp4"
            
            if job['job_type'] == JobType.SIMPLE_MERGE:
                result = video_processor.simple_merge(input_files, output_path)
            elif job['job_type'] == JobType.TRANSITION_MERGE:
                transitions = job['processing_options'].get('transitions', [])
                result = video_processor.merge_with_transitions(input_files, output_path, transitions)
            elif job['job_type'] == JobType.AUTO_EFFECTS:
                result = video_processor.apply_auto_effects(input_files, output_path, job['processing_options'])
            elif job['job_type'] == JobType.LOGO_OVERLAY:
                logo_config = job['processing_options']['logo_overlay']
                result = video_processor.add_logo_overlay(input_files, output_path, logo_config)
            elif job['job_type'] == JobType.MULTI_VIDEO:
                result = video_processor.merge_multiple_videos(input_files, output_path, job['processing_options'])
            elif job['job_type'] == JobType.PREMIUM_AI_ENHANCEMENT:
                # Delegate to premium processing task
                process_premium_video_job.delay(job_id, user_id)
                return {'success': True, 'job_id': job_id, 'message': 'Premium processing started'}
            elif job['job_type'] == JobType.AUDIO_SEPARATION:
                # Handle audio separation directly in this task
                return process_audio_separation_logic(job_id, user_id, job, db_service, storage_service, credit_manager)
            else:
                raise ValueError(f"Unsupported job type: {job['job_type']}")
            
            if not result['success']:
                raise Exception(f"Video processing failed: {result['error']}")
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'progress': 80, 'status': 'Processing completed, uploading result'}
            )
            
            # Upload result to storage
            output_filename = f"processed/{job_id}/output.mp4"
            output_url = storage_service.upload_to_storage(output_path, output_filename)
            
            # Calculate actual credits used
            actual_credits = credit_manager.calculate_actual_credits(
                job['job_type'],
                result['output_duration'],
                job['processing_options']
            )
            
            # Finalize credit transaction
            credit_manager.finalize_credits(user_uuid, estimated_credits, actual_credits, job_uuid)
            
            # Update job with results
            db_service.update_job_completion(
                job_uuid,
                JobStatus.COMPLETED,
                output_url,
                result['output_size'],
                result['output_duration'],
                actual_credits
            )
            
            # Cleanup temp files
            cleanup_temp_directory.delay(str(temp_dir))
            
            return {
                'success': True,
                'job_id': job_id,
                'output_url': output_url,
                'credits_used': actual_credits,
                'output_duration': result['output_duration']
            }
            
        finally:
            # Ensure temp directory is cleaned up even if processing fails
            if temp_dir.exists():
                cleanup_temp_directory.delay(str(temp_dir))
    
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        
        # Update job status to failed
        db_service.update_job_status(job_uuid, JobStatus.FAILED, str(e))
        
        # Refund reserved credits
        if 'estimated_credits' in locals():
            credit_manager.refund_credits(user_uuid, estimated_credits, job_uuid)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying job {job_id}, attempt {self.request.retries + 1}")
            raise self.retry_with_backoff(exc=e)
        
        return {
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }

def process_audio_separation_logic(job_id: str, user_id: str, job: dict, db_service, storage_service, credit_manager) -> Dict[str, Any]:
    """
    Audio separation logic extracted from the separate task
    """
    from services.audio_separator import AudioSeparator

    job_uuid = UUID(job_id)
    user_uuid = UUID(user_id)
    audio_separator = AudioSeparator()

    try:
        # Validate user credits
        estimated_credits = job.get('estimated_credits', 0)
        if not credit_manager.has_sufficient_credits(user_uuid, estimated_credits):
            raise ValueError("Insufficient credits for audio separation")

        # Reserve credits
        credit_manager.reserve_credits(user_uuid, estimated_credits, job_uuid)

        # Get input video
        input_video_config = job['input_config']['videos'][0]
        temp_dir = Path(tempfile.mkdtemp(prefix=f"audio_sep_{job_id}_"))

        try:
            # Download input video
            if input_video_config.get('url'):
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_file(input_video_config['url'], input_video_path)
            else:
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_from_storage(input_video_config['file_name'], input_video_path)

            # Update progress
            logger.info("Starting audio separation...")

            # Perform audio separation
            try:
                separation_result = audio_separator.separate_audio_from_video(
                    input_video_path,
                    temp_dir / "output"
                )
                logger.info(f"Audio separation completed successfully for job {job_id}")
            except Exception as audio_error:
                logger.error(f"Audio separation failed for job {job_id}: {audio_error}")
                raise audio_error

            if not separation_result['success']:
                raise Exception(f"Audio separation failed: {separation_result.get('error', 'Unknown error')}")

            # Update progress
            logger.info("Uploading separated audio files...")

            # Upload results to storage
            processing_options = job['processing_options']
            output_format = processing_options.get('output_format', 'wav')

            # Convert to desired format if needed
            voice_final_path = separation_result['separated_voice']
            music_final_path = separation_result['separated_music']

            if output_format != 'wav':
                voice_final_path = audio_separator._convert_audio_format(
                    Path(separation_result['separated_voice']),
                    temp_dir / f"voice_final.{output_format}",
                    output_format
                )
                music_final_path = audio_separator._convert_audio_format(
                    Path(separation_result['separated_music']),
                    temp_dir / f"music_final.{output_format}",
                    output_format
                )

            # Upload separated files
            voice_filename = f"audio_separation/{job_id}/voice.{output_format}"
            music_filename = f"audio_separation/{job_id}/music.{output_format}"
            original_filename = f"audio_separation/{job_id}/original.wav"

            voice_url = storage_service.upload_to_storage(Path(voice_final_path), voice_filename)
            music_url = storage_service.upload_to_storage(Path(music_final_path), music_filename)
            original_url = storage_service.upload_to_storage(Path(separation_result['original_audio']), original_filename)

            # Create mixed output if requested
            mixed_url = None
            if processing_options.get('create_mixed_output', False):
                mixed_path = temp_dir / f"mixed.{output_format}"
                audio_separator.create_mixed_output(
                    Path(voice_final_path),
                    Path(music_final_path),
                    mixed_path,
                    processing_options.get('voice_volume', 1.0),
                    processing_options.get('music_volume', 0.7)
                )
                mixed_filename = f"audio_separation/{job_id}/mixed.{output_format}"
                mixed_url = storage_service.upload_to_storage(mixed_path, mixed_filename)

            # Calculate actual credits used
            duration = separation_result['metadata'].get('duration', 0)
            actual_credits = max(5, int(duration / 60 * 10))  # 10 credits per minute, minimum 5

            # Finalize credit transaction
            credit_manager.finalize_credits(user_uuid, estimated_credits, actual_credits, job_uuid)

            # Update progress
            logger.info("Finalizing results...")

            # Update job with results
            db_service.update_job_completion(
                job_uuid,
                JobStatus.COMPLETED,
                voice_url,  # Primary output
                Path(voice_final_path).stat().st_size if Path(voice_final_path).exists() else 0,
                duration,
                actual_credits
            )

            # Cleanup temp files
            # Temporarily disable cleanup to test for .get() issue
            # cleanup_temp_directory.delay(str(temp_dir))

            return {
                'success': True,
                'job_id': job_id,
                'voice_url': voice_url,
                'music_url': music_url,
                'original_audio_url': original_url,
                'mixed_url': mixed_url,
                'credits_used': actual_credits,
                'metadata': separation_result['metadata'],
                'analysis': separation_result['analysis']
            }

        finally:
            # Ensure temp directory is cleaned up
            if temp_dir.exists():
                # Temporarily disable cleanup to test for .get() issue
                # cleanup_temp_directory.delay(str(temp_dir))
                pass

    except Exception as e:
        logger.error(f"Error processing audio separation job {job_id}: {str(e)}")

        # Update job status to failed
        db_service.update_job_status(job_uuid, JobStatus.FAILED, str(e))

        # Refund reserved credits
        if 'estimated_credits' in locals():
            credit_manager.refund_credits(user_uuid, estimated_credits, job_uuid)

        return {
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }

@celery_app.task(bind=True, queue="premium_processing")
def process_premium_video_job(self, job_id: str, user_id: str) -> Dict[str, Any]:
    """
    Premium AI-powered video processing task with step-by-step progress tracking
    """
    job_uuid = UUID(job_id)
    user_uuid = UUID(user_id)

    db_service = DatabaseService()
    storage_service = StorageService()
    credit_manager = CreditManager()
    premium_processor = PremiumVideoProcessor()

    async def progress_callback(progress):
        """Update job progress in database"""
        try:
            # Update job progress in database
            db_service.update_job_progress(
                job_uuid,
                progress.progress_percentage,
                progress.current_step.value,
                progress.completed_steps,
                progress.failed_steps,
                progress.retry_count
            )

            # Update Celery task state
            current_task.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress.progress_percentage,
                    'status': f"Step: {progress.current_step.value}",
                    'current_step': progress.current_step.value,
                    'completed_steps': [step.value for step in progress.completed_steps],
                    'failed_steps': [step.value for step in progress.failed_steps],
                    'retry_count': progress.retry_count
                }
            )
        except Exception as e:
            logger.error(f"Error updating progress for job {job_id}: {e}")

    try:
        # Update job status to processing
        db_service.update_job_status(job_uuid, JobStatus.PROCESSING)

        # Get job details
        job = db_service.get_job(job_uuid)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Validate user credits (premium jobs cost more)
        estimated_credits = job.get('estimated_credits', 0)
        if not credit_manager.has_sufficient_credits(user_uuid, estimated_credits):
            raise ValueError("Insufficient credits for premium processing")

        # Reserve credits
        credit_manager.reserve_credits(user_uuid, estimated_credits, job_uuid)

        # Get input video (premium processing typically handles single long videos)
        input_video_config = job['input_config']['videos'][0]
        temp_dir = Path(tempfile.mkdtemp(prefix=f"premium_{job_id}_"))

        try:
            # Download input video
            if input_video_config.get('url'):
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_file(input_video_config['url'], input_video_path)
            else:
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_from_storage(input_video_config['file_name'], input_video_path)

            # Get logo if specified
            logo_path = None
            processing_options = job['processing_options']
            if processing_options.get('premium_logo_overlay') and processing_options.get('logo_overlay'):
                logo_config = processing_options['logo_overlay']
                logo_path = temp_dir / "logo.png"
                storage_service.download_file(logo_config['logo_url'], logo_path)

            # Process with premium AI enhancement
            import asyncio

            async def run_premium_processing():
                return await premium_processor.process_premium_video(
                    input_video_path,
                    job_id,
                    logo_path,
                    progress_callback
                )

            # Run async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processing_result = loop.run_until_complete(run_premium_processing())
            finally:
                loop.close()

            if processing_result.error_message:
                raise Exception(f"Premium processing failed: {processing_result.error_message}")

            # Get final output
            final_output_key = 'final_assembly'
            if final_output_key not in processing_result.step_outputs:
                raise Exception("Final assembly step did not complete")

            final_output_path = Path(processing_result.step_outputs[final_output_key])

            # Upload result to storage
            output_filename = f"premium_processed/{job_id}/output.mp4"
            output_url = storage_service.upload_to_storage(final_output_path, output_filename)

            # Calculate actual credits used (premium processing uses more credits)
            actual_credits = processing_result.estimated_credits

            # Finalize credit transaction
            credit_manager.finalize_credits(user_uuid, estimated_credits, actual_credits, job_uuid)

            # Get output file info
            output_size = final_output_path.stat().st_size if final_output_path.exists() else 0

            # Get output duration using ffprobe
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(final_output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output_duration = float(result.stdout.strip()) if result.returncode == 0 else 0

            # Update job with results
            db_service.update_job_completion(
                job_uuid,
                JobStatus.COMPLETED,
                output_url,
                output_size,
                output_duration,
                actual_credits
            )

            # Cleanup temp files
            cleanup_temp_directory.delay(str(temp_dir))

            return {
                'success': True,
                'job_id': job_id,
                'output_url': output_url,
                'credits_used': actual_credits,
                'output_duration': output_duration,
                'total_effects_applied': processing_result.total_effects,
                'processing_complexity': processing_result.processing_complexity
            }

        finally:
            # Ensure temp directory is cleaned up
            if temp_dir.exists():
                cleanup_temp_directory.delay(str(temp_dir))

    except Exception as e:
        logger.error(f"Error processing premium job {job_id}: {str(e)}")

        # Update job status to failed
        db_service.update_job_status(job_uuid, JobStatus.FAILED, str(e))

        # Refund reserved credits
        if 'estimated_credits' in locals():
            credit_manager.refund_credits(user_uuid, estimated_credits, job_uuid)

        # Retry logic for premium jobs (fewer retries due to cost)
        max_premium_retries = 1
        if self.request.retries < max_premium_retries:
            logger.info(f"Retrying premium job {job_id}, attempt {self.request.retries + 1}")
            raise self.retry_with_backoff(exc=e)

        return {
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }

@celery_app.task(bind=True, queue="audio_processing")
def process_audio_separation_job(self, job_id: str, user_id: str) -> Dict[str, Any]:
    """
    Audio separation task for extracting voice and music from videos
    """
    job_uuid = UUID(job_id)
    user_uuid = UUID(user_id)

    db_service = DatabaseService()
    storage_service = StorageService()
    credit_manager = CreditManager()
    audio_separator = AudioSeparator()

    try:
        # Update job status to processing
        db_service.update_job_status(job_uuid, JobStatus.PROCESSING)

        # Get job details
        job = db_service.get_job(job_uuid)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Validate user credits
        estimated_credits = job.get('estimated_credits', 0)
        if not credit_manager.has_sufficient_credits(user_uuid, estimated_credits):
            raise ValueError("Insufficient credits for audio separation")

        # Reserve credits
        credit_manager.reserve_credits(user_uuid, estimated_credits, job_uuid)

        # Get input video
        input_video_config = job['input_config']['videos'][0]
        temp_dir = Path(tempfile.mkdtemp(prefix=f"audio_sep_{job_id}_"))

        try:
            # Download input video
            if input_video_config.get('url'):
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_file(input_video_config['url'], input_video_path)
            else:
                input_video_path = temp_dir / "input.mp4"
                storage_service.download_from_storage(input_video_config['file_name'], input_video_path)

            # Update progress
            logger.info("Starting audio separation...")
            # Temporarily disable progress updates to test for .get() issue
            # current_task.update_state(
            #     state='PROGRESS',
            #     meta={'progress': 20, 'status': 'Starting audio separation...'}
            # )

            # Perform audio separation
            try:
                separation_result = audio_separator.separate_audio_from_video(
                    input_video_path,
                    temp_dir / "output"
                )
                logger.info(f"Audio separation completed successfully for job {job_id}")
            except Exception as audio_error:
                logger.error(f"Audio separation failed for job {job_id}: {audio_error}")
                raise audio_error

            if not separation_result['success']:
                raise Exception(f"Audio separation failed: {separation_result.get('error', 'Unknown error')}")

            # Update progress
            logger.info("Uploading separated audio files...")
            # Temporarily disable progress updates to test for .get() issue
            # current_task.update_state(
            #     state='PROGRESS',
            #     meta={'progress': 70, 'status': 'Uploading separated audio files...'}
            # )

            # Upload results to storage
            processing_options = job['processing_options']
            output_format = processing_options.get('output_format', 'wav')

            # Convert to desired format if needed
            voice_final_path = separation_result['separated_voice']
            music_final_path = separation_result['separated_music']

            if output_format != 'wav':
                voice_final_path = audio_separator._convert_audio_format(
                    Path(separation_result['separated_voice']),
                    temp_dir / f"voice_final.{output_format}",
                    output_format
                )
                music_final_path = audio_separator._convert_audio_format(
                    Path(separation_result['separated_music']),
                    temp_dir / f"music_final.{output_format}",
                    output_format
                )

            # Upload separated files
            voice_filename = f"audio_separation/{job_id}/voice.{output_format}"
            music_filename = f"audio_separation/{job_id}/music.{output_format}"
            original_filename = f"audio_separation/{job_id}/original.wav"

            voice_url = storage_service.upload_to_storage(Path(voice_final_path), voice_filename)
            music_url = storage_service.upload_to_storage(Path(music_final_path), music_filename)
            original_url = storage_service.upload_to_storage(Path(separation_result['original_audio']), original_filename)

            # Create mixed output if requested
            mixed_url = None
            if processing_options.get('create_mixed_output', False):
                mixed_path = temp_dir / f"mixed.{output_format}"
                audio_separator.create_mixed_output(
                    Path(voice_final_path),
                    Path(music_final_path),
                    mixed_path,
                    processing_options.get('voice_volume', 1.0),
                    processing_options.get('music_volume', 0.7)
                )
                mixed_filename = f"audio_separation/{job_id}/mixed.{output_format}"
                mixed_url = storage_service.upload_to_storage(mixed_path, mixed_filename)

            # Calculate actual credits used
            duration = separation_result['metadata'].get('duration', 0)
            actual_credits = max(5, int(duration / 60 * 10))  # 10 credits per minute, minimum 5

            # Finalize credit transaction
            credit_manager.finalize_credits(user_uuid, estimated_credits, actual_credits, job_uuid)

            # Update progress
            logger.info("Finalizing results...")
            # Temporarily disable progress updates to test for .get() issue
            # current_task.update_state(
            #     state='PROGRESS',
            #     meta={'progress': 95, 'status': 'Finalizing results...'}
            # )

            # Prepare result data
            result_data = {
                'voice_url': voice_url,
                'music_url': music_url,
                'original_audio_url': original_url,
                'mixed_url': mixed_url,
                'metadata': separation_result['metadata'],
                'analysis': separation_result['analysis'],
                'output_format': output_format
            }

            # Update job with results
            db_service.update_job_completion(
                job_uuid,
                JobStatus.COMPLETED,
                voice_url,  # Primary output
                Path(voice_final_path).stat().st_size if Path(voice_final_path).exists() else 0,
                duration,
                actual_credits
            )

            # Cleanup temp files
            cleanup_temp_directory.delay(str(temp_dir))

            return {
                'success': True,
                'job_id': job_id,
                'voice_url': voice_url,
                'music_url': music_url,
                'original_audio_url': original_url,
                'mixed_url': mixed_url,
                'credits_used': actual_credits,
                'metadata': separation_result['metadata'],
                'analysis': separation_result['analysis']
            }

        finally:
            # Ensure temp directory is cleaned up
            if temp_dir.exists():
                cleanup_temp_directory.delay(str(temp_dir))

    except Exception as e:
        logger.error(f"Error processing audio separation job {job_id}: {str(e)}")

        # Update job status to failed
        db_service.update_job_status(job_uuid, JobStatus.FAILED, str(e))

        # Refund reserved credits
        if 'estimated_credits' in locals():
            credit_manager.refund_credits(user_uuid, estimated_credits, job_uuid)

        # Retry logic
        if self.request.retries < 2:
            logger.info(f"Retrying audio separation job {job_id}, attempt {self.request.retries + 1}")
            raise self.retry_with_backoff(exc=e)

        return {
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }

@celery_app.task(queue="video_processing")
def estimate_processing_time(job_type: str, total_duration: float, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate processing time for a job
    """
    base_time = total_duration * 2  # Base: 2x real-time
    
    # Adjust based on job type
    multipliers = {
        JobType.SIMPLE_MERGE: 1.0,
        JobType.TRANSITION_MERGE: 1.5,
        JobType.AUTO_EFFECTS: 3.0,
        JobType.LOGO_OVERLAY: 1.2,
        JobType.MULTI_VIDEO: 1.3,
        JobType.PREMIUM_AI_ENHANCEMENT: 8.0,  # Premium processing takes much longer
        JobType.AUDIO_SEPARATION: 2.0  # Audio separation is moderately intensive
    }
    
    processing_time = base_time * multipliers.get(job_type, 1.0)
    
    # Adjust for quality preset
    quality_multipliers = {
        "fast": 0.7,
        "balanced": 1.0,
        "quality": 1.8
    }
    
    quality_preset = options.get('quality_preset', 'balanced')
    processing_time *= quality_multipliers.get(quality_preset, 1.0)
    
    return {
        'estimated_seconds': int(processing_time),
        'estimated_completion': None  # Will be calculated when job starts
    }

@celery_app.task(queue="cleanup")
def cleanup_temp_directory(directory_path: str) -> bool:
    """
    Clean up temporary directory
    """
    try:
        import shutil
        temp_dir = Path(directory_path)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error cleaning up temp directory {directory_path}: {e}")
        return False

@celery_app.task(queue="video_processing")
def validate_video_files(video_urls: List[str]) -> Dict[str, Any]:
    """
    Validate video files before processing
    """
    results = []
    total_duration = 0
    
    for i, url in enumerate(video_urls):
        try:
            # Download a small portion to validate
            temp_file = f"/tmp/validate_{i}.mp4"
            
            # Use ffprobe to get video info
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = float(info['format']['duration'])
                total_duration += duration
                
                results.append({
                    'index': i,
                    'valid': True,
                    'duration': duration,
                    'format': info['format']['format_name'],
                    'size': int(info['format']['size'])
                })
            else:
                results.append({
                    'index': i,
                    'valid': False,
                    'error': result.stderr
                })
                
        except Exception as e:
            results.append({
                'index': i,
                'valid': False,
                'error': str(e)
            })
    
    return {
        'validation_results': results,
        'total_duration': total_duration,
        'all_valid': all(r['valid'] for r in results)
    }
