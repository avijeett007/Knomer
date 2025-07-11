"""
API v2 Endpoints that work with S3/Supabase URLs instead of direct file uploads
"""
import logging
import tempfile
import subprocess
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any, Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, HttpUrl, validator, Field

from services.storage_hybrid import HybridStorageService
from services.auth import AuthService
from services.credit_manager import CreditManager
from api.main import get_current_user
from config.settings import settings

logger = logging.getLogger(__name__)

# Create storage service instance
storage_service = HybridStorageService()

# Create API router
router = APIRouter(prefix="/api/v2", tags=["v2"])

# Define input models for URL-based operations
class LogoOverlayRequest(BaseModel):
    video_url: HttpUrl
    logo_url: HttpUrl
    position: str = Field("top-right", description="Position: top-left, top-right, bottom-left, bottom-right, center")
    opacity: float = Field(0.8, ge=0.0, le=1.0)
    scale: float = Field(0.2, gt=0.0, le=1.0)
    
    @validator('position')
    def validate_position(cls, v):
        valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
        if v not in valid_positions:
            raise ValueError(f"Position must be one of: {', '.join(valid_positions)}")
        return v

class VideoMergeRequest(BaseModel):
    video_urls: List[HttpUrl]
    transition_type: str = Field("fade", description="Transition effect between videos")
    transition_duration: float = Field(1.0, ge=0.0, le=5.0)

class VideoTransitionRequest(BaseModel):
    video_urls: List[HttpUrl]
    transition_type: str = Field("fade", description="Transition effect: fade, wipe, dissolve, zoom")
    transition_duration: float = Field(1.0, ge=0.0, le=5.0)
    
    @validator('transition_type')
    def validate_transition(cls, v):
        valid_transitions = ["fade", "wipe", "dissolve", "zoom", "slide", "blur"]
        if v not in valid_transitions:
            raise ValueError(f"Transition must be one of: {', '.join(valid_transitions)}")
        return v

class PremiumProcessRequest(BaseModel):
    video_url: HttpUrl
    effects: List[str] = Field([], description="List of AI effects to apply")
    resolution: str = Field("720p", description="Output resolution: 720p, 1080p, 4K")
    
    @validator('resolution')
    def validate_resolution(cls, v):
        valid_resolutions = ["720p", "1080p", "4K"]
        if v not in valid_resolutions:
            raise ValueError(f"Resolution must be one of: {', '.join(valid_resolutions)}")
        return v

# Import DB service for job status
if settings.USE_SQLITE:
    from services.database_sqlite import SQLiteDatabaseService as DatabaseService
else:
    from services.database import DatabaseService

# Create database service instance
db_service = DatabaseService()

@router.post("/logo-overlay", summary="Add logo overlay to video (URL input)")
async def logo_overlay_url(
    request: LogoOverlayRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Add logo overlay to video using URL inputs instead of file uploads
    
    This endpoint accepts public URLs for video and logo files and returns a public URL for the processed video
    """
    try:
        job_id = str(uuid4())
        
        # Create temp directory for processing
        temp_dir = Path(tempfile.mkdtemp(prefix=f"logo_job_{job_id}_"))
        
        # Download input files
        video_path = temp_dir / f"input_video_{job_id}.mp4"
        logo_path = temp_dir / f"logo_{job_id}.png"
        
        # Download files asynchronously
        video_file = await storage_service.download_from_url(str(request.video_url), video_path)
        logo_file = await storage_service.download_from_url(str(request.logo_url), logo_path)
        
        if not video_file or not logo_file:
            raise HTTPException(status_code=400, detail="Failed to download input files")
            
        # Get video duration
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_seconds = float(result.stdout.strip()) if result.returncode == 0 else 60
        
        # Create output file path
        output_filename = f"{job_id}_logo.mp4"
        output_path = temp_dir / output_filename
        
        # Position mapping for FFmpeg overlay filter
        position_map = {
            "top-left": "10:10",
            "top-right": "W-w-10:10",
            "bottom-left": "10:H-h-10",
            "bottom-right": "W-w-10:H-h-10",
            "center": "(W-w)/2:(H-h)/2"
        }
        
        overlay_position = position_map.get(request.position, "W-w-10:10")
        
        # Create FFmpeg command for logo overlay
        ffmpeg_cmd = [
            'ffmpeg', '-i', str(video_path), '-i', str(logo_path),
            '-filter_complex',
            f'[1:v]scale=iw*{request.scale}:ih*{request.scale}[logo];[0:v][logo]overlay={overlay_position}:format=auto,format=yuv420p',
            '-c:a', 'copy', str(output_path), '-y'
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg overlay error: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to add logo overlay")
        
        # Upload result to storage
        output_url = storage_service.upload_output_file(output_path, output_filename)
        
        if not output_url:
            raise HTTPException(status_code=500, detail="Failed to upload result")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        # Calculate credits (1.2x for logo overlay)
        estimated_credits = max(1, int(duration_seconds / 10 * 1.2))
        
        # Return success response
        return {
            "success": True,
            "job_id": job_id,
            "estimated_credits": estimated_credits,
            "duration_seconds": duration_seconds,
            "overlay_settings": {
                "position": request.position,
                "opacity": request.opacity,
                "scale": request.scale
            },
            "status": "completed",
            "message": "Logo overlay completed successfully",
            "output_url": output_url
        }
        
    except Exception as e:
        logger.error(f"Logo overlay failed: {e}")
        raise HTTPException(status_code=500, detail=f"Logo overlay failed: {str(e)}")

@router.post("/merge", summary="Merge multiple videos (URL input)")
async def merge_videos_url(
    request: VideoMergeRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Merge multiple videos using URL inputs instead of file uploads
    
    This endpoint accepts a list of public video URLs and returns a public URL for the merged video
    """
    try:
        job_id = str(uuid4())
        
        # Create temp directory for processing
        temp_dir = Path(tempfile.mkdtemp(prefix=f"merge_job_{job_id}_"))
        
        # Download input videos
        input_files = []
        total_duration = 0
        
        for i, video_url in enumerate(request.video_urls):
            input_path = temp_dir / f"input_{i}_{job_id}.mp4"
            
            # Download file
            downloaded_file = await storage_service.download_from_url(str(video_url), input_path)
            
            if not downloaded_file:
                raise HTTPException(status_code=400, detail=f"Failed to download video {i+1}")
                
            input_files.append(str(input_path))
            
            # Get video duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(input_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                total_duration += duration
        
        # Create output file path
        output_filename = f"{job_id}_merged.mp4"
        output_path = temp_dir / output_filename
        
        # Create FFmpeg concat file
        concat_file = temp_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for input_file in input_files:
                f.write(f"file '{input_file}'\n")
        
        # Run FFmpeg to merge videos
        ffmpeg_cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-c', 'copy', str(output_path), '-y'
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg merge error: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to merge videos")
        
        # Upload result to storage
        output_url = storage_service.upload_output_file(output_path, output_filename)
        
        if not output_url:
            raise HTTPException(status_code=500, detail="Failed to upload result")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        # Calculate credits (1x for simple merge)
        estimated_credits = max(1, int(total_duration / 10))
        
        # Return success response
        return {
            "success": True,
            "job_id": job_id,
            "estimated_credits": estimated_credits,
            "duration_seconds": total_duration,
            "video_count": len(input_files),
            "status": "completed",
            "message": "Videos merged successfully",
            "output_url": output_url
        }
        
    except Exception as e:
        logger.error(f"Video merge failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video merge failed: {str(e)}")

@router.post("/merge-with-transitions", summary="Merge videos with transitions (URL input)")
async def merge_with_transitions_url(
    request: VideoTransitionRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Merge videos with transitions using URL inputs instead of file uploads
    
    This endpoint accepts a list of public video URLs and returns a public URL for the merged video with transitions
    """
    try:
        job_id = str(uuid4())
        
        # Create temp directory for processing
        temp_dir = Path(tempfile.mkdtemp(prefix=f"transition_job_{job_id}_"))
        
        # Download input videos
        input_files = []
        total_duration = 0
        
        for i, video_url in enumerate(request.video_urls):
            input_path = temp_dir / f"input_{i}_{job_id}.mp4"
            
            # Download file
            downloaded_file = await storage_service.download_from_url(str(video_url), input_path)
            
            if not downloaded_file:
                raise HTTPException(status_code=400, detail=f"Failed to download video {i+1}")
                
            input_files.append(str(input_path))
            
            # Get video duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(input_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                total_duration += duration
        
        # Create output file path
        output_filename = f"{job_id}_transitioned.mp4"
        output_path = temp_dir / output_filename
        
        # Build complex FFmpeg filter graph for transitions
        filter_complex = []
        input_args = []
        
        for i, input_file in enumerate(input_files):
            input_args.extend(['-i', input_file])
            
        # Define transition based on type
        transition_filters = {
            "fade": f"xfade=transition=fade:duration={request.transition_duration}",
            "wipe": f"xfade=transition=wiperight:duration={request.transition_duration}",
            "dissolve": f"xfade=transition=dissolve:duration={request.transition_duration}",
            "zoom": f"xfade=transition=radial:duration={request.transition_duration}",
            "slide": f"xfade=transition=slideright:duration={request.transition_duration}",
            "blur": f"xfade=transition=smoothright:duration={request.transition_duration}"
        }
        
        transition_filter = transition_filters.get(request.transition_type, transition_filters["fade"])
        
        # Build filter complex for xfade transitions between clips
        filter_parts = []
        for i in range(len(input_files) - 1):
            if i == 0:
                filter_parts.append(f"[0][1]{transition_filter}:offset={total_duration/(len(input_files)*2)}[t1]")
            else:
                filter_parts.append(f"[t{i}][{i+1}]{transition_filter}:offset={total_duration/(len(input_files)*2)}[t{i+1}]")
        
        filter_complex = ";".join(filter_parts)
        
        # Run FFmpeg with xfade filter for transitions
        ffmpeg_cmd = [
            'ffmpeg',
            *input_args,
            '-filter_complex', filter_complex,
            '-map', f"[t{len(input_files)-1}]",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            str(output_path),
            '-y'
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        # Fallback to simpler method if complex transitions fail
        if result.returncode != 0:
            logger.warning(f"Complex transitions failed, using simpler method: {result.stderr}")
            
            # Create concat file with crossfade hints
            concat_file = temp_dir / "xfade.txt"
            with open(concat_file, "w") as f:
                for i, input_file in enumerate(input_files):
                    f.write(f"file '{input_file}'\n")
                    if i < len(input_files) - 1:
                        f.write(f"duration {request.transition_duration}\n")
            
            # Use simple concat with crossfade
            ffmpeg_cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                '-vf', f"xfade=transition={request.transition_type}:duration={request.transition_duration}",
                str(output_path), '-y'
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg transitions error: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to create transitions")
        
        # Upload result to storage
        output_url = storage_service.upload_output_file(output_path, output_filename)
        
        if not output_url:
            raise HTTPException(status_code=500, detail="Failed to upload result")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        # Calculate credits (1.5x for transitions)
        estimated_credits = max(1, int(total_duration / 10 * 1.5))
        
        # Return success response
        return {
            "success": True,
            "job_id": job_id,
            "estimated_credits": estimated_credits,
            "duration_seconds": total_duration,
            "video_count": len(input_files),
            "transition": request.transition_type,
            "transition_duration": request.transition_duration,
            "status": "completed",
            "message": "Videos merged with transitions successfully",
            "output_url": output_url
        }
        
    except Exception as e:
        logger.error(f"Video transitions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video transitions failed: {str(e)}")

@router.post("/premium/process", summary="Apply premium effects to video (URL input)")
async def premium_process_url(
    request: PremiumProcessRequest,
    user_info: dict = Depends(get_current_user)
):
    """
    Apply premium AI effects to video using URL input instead of file upload
    
    This endpoint accepts a public video URL and returns a public URL for the processed video
    """
    try:
        job_id = str(uuid4())
        
        # Verify premium subscription
        if user_info.get('subscription_tier') not in ['premium', 'enterprise']:
            raise HTTPException(status_code=403, detail="Premium subscription required")
        
        # Create temp directory for processing
        temp_dir = Path(tempfile.mkdtemp(prefix=f"premium_job_{job_id}_"))
        
        # Download input video
        video_path = temp_dir / f"input_{job_id}.mp4"
        
        # Download file
        downloaded_file = await storage_service.download_from_url(str(request.video_url), video_path)
        
        if not downloaded_file:
            raise HTTPException(status_code=400, detail="Failed to download video")
            
        # Get video duration
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_seconds = float(result.stdout.strip()) if result.returncode == 0 else 60
        
        # Create output file path
        output_filename = f"{job_id}_premium.mp4"
        output_path = temp_dir / output_filename
        
        # Apply premium effects (simplified example)
        filters = []
        
        # Resolution mapping
        resolution_map = {
            "720p": "1280:720",
            "1080p": "1920:1080",
            "4K": "3840:2160"
        }
        
        target_resolution = resolution_map.get(request.resolution, "1280:720")
        
        # Add scale filter for resolution
        filters.append(f"scale={target_resolution}")
        
        # Add requested effects
        for effect in request.effects:
            if effect == "enhance":
                filters.append("unsharp=5:5:1.5:5:5:0.0")
            elif effect == "stabilize":
                filters.append("deshake=x=16:y=16:rx=64:ry=64")
            elif effect == "denoise":
                filters.append("hqdn3d=4:4:8:8")
            elif effect == "brighten":
                filters.append("eq=brightness=0.1")
            elif effect == "contrast":
                filters.append("eq=contrast=1.2")
        
        # Build filter chain
        filter_chain = ",".join(filters)
        
        # Run FFmpeg with effects
        ffmpeg_cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vf', filter_chain,
            '-c:v', 'libx264', 
            '-preset', 'slow', 
            '-crf', '18',
            '-c:a', 'aac', 
            '-b:a', '192k',
            str(output_path),
            '-y'
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Premium processing error: {result.stderr}")
            raise HTTPException(status_code=500, detail="Failed to process video")
        
        # Upload result to storage
        output_url = storage_service.upload_output_file(output_path, output_filename)
        
        if not output_url:
            raise HTTPException(status_code=500, detail="Failed to upload result")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        # Calculate credits (2x for premium effects)
        estimated_credits = max(2, int(duration_seconds / 10 * 2))
        
        # Return success response
        return {
            "success": True,
            "job_id": job_id,
            "estimated_credits": estimated_credits,
            "duration_seconds": duration_seconds,
            "effects": request.effects,
            "resolution": request.resolution,
            "status": "completed",
            "message": "Premium processing completed successfully",
            "output_url": output_url
        }
        
    except Exception as e:
        logger.error(f"Premium processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Premium processing failed: {str(e)}")


@router.get("/jobs/{job_id}", summary="Get job status with direct download URLs")
async def get_job_status(job_id: str, user_info: dict = Depends(get_current_user)):
    """
    Get status of a job with direct download URLs instead of internal URLs
    
    This endpoint returns the job status, with S3/Supabase URLs for output files if available
    """
    try:
        # Convert string job ID to UUID if needed
        from uuid import UUID
        if isinstance(job_id, str):
            try:
                job_id = UUID(job_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid job ID format")
                
        # Get job from database
        job = db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        # Check if user owns this job
        if job['user_id'] != user_info['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
            
        # Parse datetime fields if they're strings
        def parse_datetime(dt_str):
            from datetime import datetime
            if dt_str and isinstance(dt_str, str):
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt_str
            
        # Prepare response with properly formatted URLs
        output_url = job.get('output_file_url')
        
        # If we have an output URL that's a local path or needs to be converted to S3/Supabase URL
        if output_url and output_url.startswith("/api/v1/download/"):
            # Replace with SERVER_URL or Supabase URL
            if storage_service.use_cloud_output:
                # If using cloud storage, get the S3/Supabase URL
                filename = os.path.basename(output_url)
                output_path = f"outputs/{filename}"
                storage_url = storage_service.get_public_url(output_path)
                if storage_url:
                    output_url = storage_url
            else:
                # If using local storage with SERVER_URL
                from urllib.parse import urljoin
                output_url = urljoin(settings.SERVER_URL, output_url)
                
        # Return job response with proper URLs
        return {
            "id": str(job_id),
            "job_type": job['job_type'],
            "status": job['status'],
            "estimated_credits": job.get('estimated_credits'),
            "actual_credits_used": job.get('actual_credits_used'),
            "created_at": parse_datetime(job['created_at']),
            "started_at": parse_datetime(job.get('started_at')),
            "completed_at": parse_datetime(job.get('completed_at')),
            "error_message": job.get('error_message'),
            "output_url": output_url,
            "download_expires_at": parse_datetime(job.get('download_expires_at')),
            "download_count": job.get('download_count', 0),
            "progress_percentage": None  # Could be extended to get from Celery task
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")


@router.get("/jobs", summary="List all jobs with direct download URLs")
async def list_jobs(user_info: dict = Depends(get_current_user)):
    """
    List all jobs for the current user with direct download URLs
    
    This endpoint returns a list of jobs, with S3/Supabase URLs for output files if available
    """
    try:
        # Get user ID from auth
        user_id = user_info['user_id']
        
        # Get jobs from database
        jobs = db_service.get_user_jobs(user_id)
        
        # Process each job to ensure URLs are correct
        processed_jobs = []
        for job in jobs:
            # Process output URL
            output_url = job.get('output_file_url')
            
            # If we have an output URL that's a local path or needs to be converted to S3/Supabase URL
            if output_url and output_url.startswith("/api/v1/download/"):
                # Replace with SERVER_URL or Supabase URL
                if storage_service.use_cloud_output:
                    # If using cloud storage, get the S3/Supabase URL
                    filename = os.path.basename(output_url)
                    output_path = f"outputs/{filename}"
                    storage_url = storage_service.get_public_url(output_path)
                    if storage_url:
                        output_url = storage_url
                else:
                    # If using local storage with SERVER_URL
                    from urllib.parse import urljoin
                    output_url = urljoin(settings.SERVER_URL, output_url)
                    
            # Parse datetime fields
            def parse_datetime(dt_str):
                from datetime import datetime
                if dt_str and isinstance(dt_str, str):
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt_str
                
            # Add processed job to list
            processed_jobs.append({
                "id": job['id'],
                "job_type": job['job_type'],
                "status": job['status'],
                "created_at": parse_datetime(job['created_at']),
                "completed_at": parse_datetime(job.get('completed_at')),
                "output_url": output_url
            })
            
        return {"jobs": processed_jobs}
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")

