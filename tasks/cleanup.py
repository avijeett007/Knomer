"""
Cleanup tasks for maintaining system health
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from celery_app import celery_app
from services.database import DatabaseService
from services.storage import StorageService
from config.settings import settings

logger = logging.getLogger(__name__)

@celery_app.task(queue="cleanup")
def cleanup_temp_files() -> Dict[str, Any]:
    """
    Clean up temporary files older than configured threshold
    """
    cleaned_count = 0
    total_size_freed = 0
    errors = []
    
    try:
        temp_dir = Path(settings.TEMP_STORAGE_PATH)
        if not temp_dir.exists():
            return {
                'success': True,
                'cleaned_count': 0,
                'size_freed_mb': 0,
                'message': 'Temp directory does not exist'
            }
        
        cutoff_time = datetime.now() - timedelta(hours=settings.TEMP_FILE_CLEANUP_HOURS)
        
        for file_path in temp_dir.rglob('*'):
            try:
                if file_path.is_file():
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_count += 1
                        total_size_freed += file_size
                        logger.debug(f"Cleaned up temp file: {file_path}")
                
                elif file_path.is_dir() and not any(file_path.iterdir()):
                    # Remove empty directories
                    file_path.rmdir()
                    logger.debug(f"Removed empty directory: {file_path}")
                    
            except Exception as e:
                error_msg = f"Error cleaning {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        size_freed_mb = total_size_freed / (1024 * 1024)
        
        logger.info(f"Cleanup completed: {cleaned_count} files, {size_freed_mb:.2f} MB freed")
        
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'size_freed_mb': round(size_freed_mb, 2),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error during temp file cleanup: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'cleaned_count': cleaned_count,
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2)
        }

@celery_app.task(queue="cleanup")
def cleanup_expired_jobs() -> Dict[str, Any]:
    """
    Clean up expired job files and update database
    """
    db_service = DatabaseService()
    storage_service = StorageService()
    
    cleaned_jobs = 0
    cleaned_files = 0
    total_size_freed = 0
    errors = []
    
    try:
        # Get expired jobs
        cutoff_time = datetime.utcnow() - timedelta(days=settings.OUTPUT_FILE_RETENTION_DAYS)
        expired_jobs = db_service.get_expired_jobs(cutoff_time)
        
        for job in expired_jobs:
            try:
                job_id = job['id']
                
                # Delete output file from storage
                if job.get('output_file_url'):
                    file_size = storage_service.delete_file(job['output_file_url'])
                    if file_size:
                        total_size_freed += file_size
                        cleaned_files += 1
                
                # Delete associated video files
                video_files = db_service.get_job_video_files(job_id)
                for video_file in video_files:
                    if video_file.get('file_url') and video_file.get('is_temporary'):
                        file_size = storage_service.delete_file(video_file['file_url'])
                        if file_size:
                            total_size_freed += file_size
                            cleaned_files += 1
                
                # Mark job as cleaned up
                db_service.mark_job_cleaned_up(job_id)
                cleaned_jobs += 1
                
                logger.debug(f"Cleaned up expired job: {job_id}")
                
            except Exception as e:
                error_msg = f"Error cleaning job {job.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        size_freed_mb = total_size_freed / (1024 * 1024)
        
        logger.info(f"Expired job cleanup: {cleaned_jobs} jobs, {cleaned_files} files, {size_freed_mb:.2f} MB freed")
        
        return {
            'success': True,
            'cleaned_jobs': cleaned_jobs,
            'cleaned_files': cleaned_files,
            'size_freed_mb': round(size_freed_mb, 2),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error during expired job cleanup: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'cleaned_jobs': cleaned_jobs,
            'cleaned_files': cleaned_files
        }

@celery_app.task(queue="cleanup")
def cleanup_failed_jobs() -> Dict[str, Any]:
    """
    Clean up files from failed jobs older than 24 hours
    """
    db_service = DatabaseService()
    storage_service = StorageService()
    
    cleaned_count = 0
    total_size_freed = 0
    
    try:
        # Get failed jobs older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        failed_jobs = db_service.get_failed_jobs_before(cutoff_time)
        
        for job in failed_jobs:
            try:
                job_id = job['id']
                
                # Delete any partial output files
                video_files = db_service.get_job_video_files(job_id)
                for video_file in video_files:
                    if video_file.get('file_url') and video_file.get('is_temporary'):
                        file_size = storage_service.delete_file(video_file['file_url'])
                        if file_size:
                            total_size_freed += file_size
                
                # Mark as cleaned up
                db_service.mark_job_cleaned_up(job_id)
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Error cleaning failed job {job.get('id')}: {str(e)}")
        
        size_freed_mb = total_size_freed / (1024 * 1024)
        
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'size_freed_mb': round(size_freed_mb, 2)
        }
        
    except Exception as e:
        logger.error(f"Error during failed job cleanup: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@celery_app.task(queue="cleanup")
def update_system_stats() -> Dict[str, Any]:
    """
    Update system statistics for monitoring
    """
    db_service = DatabaseService()
    
    try:
        stats = {
            'timestamp': datetime.utcnow(),
            'total_jobs': db_service.count_total_jobs(),
            'active_jobs': db_service.count_active_jobs(),
            'completed_jobs_24h': db_service.count_completed_jobs_last_24h(),
            'failed_jobs_24h': db_service.count_failed_jobs_last_24h(),
            'total_credits_consumed': db_service.sum_credits_consumed(),
            'active_users_24h': db_service.count_active_users_last_24h(),
            'average_processing_time': db_service.get_average_processing_time(),
            'storage_usage_mb': db_service.get_total_storage_usage() / (1024 * 1024)
        }
        
        # Store stats in database or cache
        db_service.store_system_stats(stats)
        
        logger.info(f"Updated system stats: {stats['active_jobs']} active jobs, {stats['completed_jobs_24h']} completed in 24h")
        
        return {
            'success': True,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error updating system stats: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@celery_app.task(queue="cleanup")
def cleanup_old_rate_limit_records() -> Dict[str, Any]:
    """
    Clean up old rate limiting records
    """
    db_service = DatabaseService()
    
    try:
        # Remove rate limit records older than 1 day
        cutoff_time = datetime.utcnow() - timedelta(days=1)
        deleted_count = db_service.cleanup_old_rate_limits(cutoff_time)
        
        logger.info(f"Cleaned up {deleted_count} old rate limit records")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up rate limit records: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@celery_app.task(queue="cleanup")
def health_check_cleanup() -> Dict[str, Any]:
    """
    Perform health checks and cleanup if needed
    """
    # Schedule cleanup tasks without waiting for results
    cleanup_temp_files.delay()
    cleanup_expired_jobs.delay()
    cleanup_failed_jobs.delay()
    cleanup_old_rate_limit_records.delay()
    update_system_stats.delay()

    return {
        'success': True,
        'message': 'Cleanup tasks scheduled',
        'timestamp': datetime.utcnow()
    }
