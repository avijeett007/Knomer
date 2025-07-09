"""
Premium Video Processing API Endpoints

Provides AI-powered video enhancement with:
- Smart zooming based on content analysis
- Intelligent captioning placement
- Logo overlay optimization
- Step-by-step progress tracking
- Retry and recovery mechanisms
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging
from pathlib import Path
import tempfile
import json
from uuid import uuid4
from enum import Enum

# Define JobType and JobStatus locally if not available
class JobType(Enum):
    PREMIUM_PROCESSING = "premium_ai_enhancement"

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

from services.auth import AuthService
from services.database_sqlite import SQLiteDatabaseService
from services.credit_manager import CreditManager
from services.storage_local import LocalStorageService
from tasks.premium_video_processing import process_premium_video_job

# Initialize services
auth_service = AuthService()
security = HTTPBearer()

def get_database_service():
    return SQLiteDatabaseService()

def get_storage_service():
    return LocalStorageService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from API key"""
    api_key = credentials.credentials
    user_info = await auth_service.validate_api_key(api_key)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/premium", tags=["premium-processing"])

@router.post("/estimate-credits")
async def estimate_premium_credits(
    video_file: UploadFile = File(...),
    enable_smart_zooming: bool = Form(True),
    enable_smart_captioning: bool = Form(True),
    enable_logo_overlay: bool = Form(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Estimate credits required for premium video processing
    
    Base rate: 100 credits per minute
    Complexity multipliers:
    - Simple: 1.0x
    - Moderate: 1.2x  
    - Complex: 1.5x
    """
    try:
        # Save uploaded video temporarily for analysis
        temp_dir = Path(tempfile.mkdtemp(prefix="premium_estimate_"))
        video_path = temp_dir / f"input_{video_file.filename}"
        
        with open(video_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        # Get video duration using ffprobe
        import subprocess
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail="Invalid video file")
        
        duration_seconds = float(result.stdout.strip())
        duration_minutes = duration_seconds / 60
        
        # Base credit calculation
        base_credits = int(duration_minutes * 100)
        
        # Feature multipliers
        feature_multiplier = 1.0
        if enable_smart_zooming:
            feature_multiplier += 0.2
        if enable_smart_captioning:
            feature_multiplier += 0.3
        if enable_logo_overlay:
            feature_multiplier += 0.1
        
        # Estimated complexity (would be determined by AI analysis in full processing)
        estimated_complexity = "moderate"  # Default assumption
        complexity_multiplier = {"simple": 1.0, "moderate": 1.2, "complex": 1.5}[estimated_complexity]
        
        total_credits = int(base_credits * feature_multiplier * complexity_multiplier)
        
        # Cleanup temp file
        video_path.unlink()
        temp_dir.rmdir()
        
        return {
            "estimated_credits": total_credits,
            "duration_seconds": duration_seconds,
            "duration_minutes": round(duration_minutes, 2),
            "base_credits": base_credits,
            "feature_multiplier": feature_multiplier,
            "complexity_multiplier": complexity_multiplier,
            "breakdown": {
                "base_cost": base_credits,
                "smart_zooming": int(base_credits * 0.2) if enable_smart_zooming else 0,
                "smart_captioning": int(base_credits * 0.3) if enable_smart_captioning else 0,
                "logo_overlay": int(base_credits * 0.1) if enable_logo_overlay else 0,
                "complexity_adjustment": int(base_credits * (complexity_multiplier - 1.0))
            },
            "features_enabled": {
                "smart_zooming": enable_smart_zooming,
                "smart_captioning": enable_smart_captioning,
                "logo_overlay": enable_logo_overlay
            }
        }
        
    except Exception as e:
        logger.error(f"Credit estimation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Credit estimation failed: {str(e)}")

@router.post("/process")
async def create_premium_processing_job(
    video_file: UploadFile = File(...),
    logo_file: Optional[UploadFile] = File(None),
    enable_smart_zooming: bool = Form(True),
    enable_smart_captioning: bool = Form(True),
    enable_logo_overlay: bool = Form(False),
    processing_quality: str = Form("high"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a premium video processing job with AI-powered effects
    
    Features:
    - AI-powered smart zooming based on content analysis
    - Intelligent captioning placement using LLM analysis
    - Optimized logo overlay positioning
    - Step-by-step progress tracking with retry capability
    """
    try:
        db_service = get_database_service()
        storage_service = get_storage_service()
        credit_manager = CreditManager(db_service)
        
        # Generate job ID
        job_id = str(uuid4())
        user_id = current_user['user_id']
        
        # Estimate credits (quick estimation)
        temp_dir = Path(tempfile.mkdtemp(prefix=f"premium_job_{job_id}_"))
        video_path = temp_dir / f"input_{video_file.filename}"
        
        with open(video_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        # Get video duration
        import subprocess
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_seconds = float(result.stdout.strip())
        duration_minutes = duration_seconds / 60
        
        # Calculate estimated credits
        base_credits = int(duration_minutes * 100)
        feature_multiplier = 1.0
        if enable_smart_zooming:
            feature_multiplier += 0.2
        if enable_smart_captioning:
            feature_multiplier += 0.3
        if enable_logo_overlay:
            feature_multiplier += 0.1
        
        estimated_credits = int(base_credits * feature_multiplier * 1.2)  # Moderate complexity assumption
        
        # Check user credits
        if not credit_manager.has_sufficient_credits(user_id, estimated_credits):
            raise HTTPException(
                status_code=402, 
                detail=f"Insufficient credits. Required: {estimated_credits}, Available: {credit_manager.get_user_credits(user_id)}"
            )
        
        # Reserve credits
        credit_manager.reserve_credits(user_id, estimated_credits, job_id)
        
        # Handle logo file if provided
        logo_path = None
        if logo_file and enable_logo_overlay:
            logo_path = temp_dir / f"logo_{logo_file.filename}"
            with open(logo_path, "wb") as f:
                logo_content = await logo_file.read()
                f.write(logo_content)
        
        # Create job configuration
        job_config = {
            "job_id": job_id,
            "job_type": JobType.PREMIUM_PROCESSING,
            "user_id": user_id,
            "input_config": {
                "video_path": str(video_path),
                "logo_path": str(logo_path) if logo_path else None,
                "duration_seconds": duration_seconds
            },
            "processing_options": {
                "enable_smart_zooming": enable_smart_zooming,
                "enable_smart_captioning": enable_smart_captioning,
                "enable_logo_overlay": enable_logo_overlay,
                "processing_quality": processing_quality,
                "max_zoom_duration": 3.0,
                "min_zoom_duration": 0.5,
                "caption_style": "dynamic",
                "logo_opacity": 0.8
            },
            "estimated_credits": estimated_credits
        }
        
        # Create job in database
        db_service.create_job(
            job_id=job_id,
            user_id=user_id,
            job_type=JobType.PREMIUM_PROCESSING,
            input_config=job_config["input_config"],
            processing_options=job_config["processing_options"],
            estimated_credits=estimated_credits,
            status=JobStatus.PENDING
        )
        
        # Submit job to Celery
        process_premium_video_job.delay(job_config)
        
        return {
            "success": True,
            "job_id": job_id,
            "estimated_credits": estimated_credits,
            "duration_seconds": duration_seconds,
            "features_enabled": {
                "smart_zooming": enable_smart_zooming,
                "smart_captioning": enable_smart_captioning,
                "logo_overlay": enable_logo_overlay
            },
            "status": "pending",
            "message": "Premium processing job created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Premium processing job creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_premium_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed status of a premium processing job"""
    try:
        db_service = get_database_service()
        
        # Get job details
        job = db_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify job ownership
        if job['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get detailed progress if available
        progress_data = db_service.get_job_progress(job_id)
        
        return {
            "job_id": job_id,
            "status": job['status'],
            "created_at": job['created_at'],
            "completed_at": job.get('completed_at'),
            "output_file_url": job.get('output_file_url'),
            "estimated_credits": job['estimated_credits'],
            "actual_credits_used": job.get('actual_credits_used'),
            "progress": progress_data,
            "processing_options": job['processing_options'],
            "error_message": job.get('error_message')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")

@router.post("/jobs/{job_id}/retry")
async def retry_premium_job(
    job_id: str,
    retry_from_step: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Retry a failed premium processing job from a specific step"""
    try:
        db_service = get_database_service()
        
        # Get job details
        job = db_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify job ownership
        if job['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if job can be retried
        if job['status'] not in [JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Job cannot be retried")
        
        # Update job status to pending
        db_service.update_job_status(job_id, JobStatus.PENDING)
        
        # Resubmit job with retry configuration
        retry_config = {
            "job_id": job_id,
            "retry_from_step": retry_from_step,
            "original_config": {
                "input_config": job['input_config'],
                "processing_options": job['processing_options']
            }
        }
        
        # Submit retry job
        from ...tasks.premium_video_processing import retry_premium_video_job
        retry_premium_video_job.delay(retry_config)
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Job retry initiated{f' from step {retry_from_step}' if retry_from_step else ''}",
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job retry failed: {e}")
        raise HTTPException(status_code=500, detail="Job retry failed")

@router.get("/jobs/{job_id}/progress")
async def get_job_progress(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get real-time progress of a premium processing job"""
    try:
        db_service = get_database_service()
        
        # Verify job ownership
        job = db_service.get_job(job_id)
        if not job or job['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get detailed progress
        progress = db_service.get_job_progress(job_id)
        
        return {
            "job_id": job_id,
            "current_step": progress.get('current_step'),
            "completed_steps": progress.get('completed_steps', []),
            "failed_steps": progress.get('failed_steps', []),
            "progress_percentage": progress.get('progress_percentage', 0),
            "step_outputs": progress.get('step_outputs', {}),
            "estimated_completion": progress.get('estimated_completion'),
            "error_message": progress.get('error_message')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job progress")
