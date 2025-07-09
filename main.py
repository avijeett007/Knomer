import os
import uuid
import tempfile
import shutil
from pathlib import Path
from typing import List
import subprocess
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Merger API",
    description="FastAPI server for merging videos using FFmpeg",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for processing
TEMP_DIR = Path(tempfile.gettempdir()) / "video_merger"
TEMP_DIR.mkdir(exist_ok=True)

def cleanup_old_files():
    """Clean up files older than 1 hour"""
    try:
        import time
        current_time = time.time()
        for file_path in TEMP_DIR.glob("*"):
            if file_path.is_file() and (current_time - file_path.stat().st_mtime) > 3600:
                file_path.unlink()
                logger.info(f"Cleaned up old file: {file_path}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False

def merge_videos(original_path: Path, ending_path: Path, output_path: Path) -> bool:
    """Merge two videos using FFmpeg"""
    try:
        # FFmpeg command to concatenate videos
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-i", str(original_path),
            "-i", str(ending_path),
            "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            str(output_path)
        ]
        
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
        return output_path.exists()
        
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg process timed out")
        return False
    except Exception as e:
        logger.error(f"Error merging videos: {e}")
        return False

@app.get("/")
async def root():
    """Health check endpoint"""
    ffmpeg_available = check_ffmpeg()
    return {
        "message": "Video Merger API is running",
        "ffmpeg_available": ffmpeg_available,
        "temp_dir": str(TEMP_DIR)
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    ffmpeg_available = check_ffmpeg()
    temp_dir_writable = os.access(TEMP_DIR, os.W_OK)
    
    return {
        "status": "healthy" if ffmpeg_available and temp_dir_writable else "unhealthy",
        "ffmpeg_available": ffmpeg_available,
        "temp_dir_writable": temp_dir_writable,
        "temp_dir_path": str(TEMP_DIR)
    }

@app.post("/merge-videos")
async def merge_videos_endpoint(
    original_video: UploadFile = File(..., description="Original video file"),
    ending_video: UploadFile = File(..., description="Ending video file"),
    platform: str = Form(..., description="Platform name (youtube, instagram, tiktok)")
):
    """
    Merge two video files and return the merged video
    """
    # Cleanup old files
    cleanup_old_files()
    
    # Check FFmpeg availability
    if not check_ffmpeg():
        raise HTTPException(status_code=500, detail="FFmpeg is not available on this server")
    
    # Validate file types
    allowed_types = ["video/mp4", "video/mpeg", "video/quicktime"]
    if original_video.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Original video must be MP4, MPEG, or MOV. Got: {original_video.content_type}")
    
    if ending_video.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Ending video must be MP4, MPEG, or MOV. Got: {ending_video.content_type}")
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    try:
        # Save uploaded files
        original_path = session_dir / f"original_{original_video.filename}"
        ending_path = session_dir / f"ending_{ending_video.filename}"
        output_path = session_dir / f"merged_{platform}_{session_id}.mp4"
        
        # Write files to disk
        with open(original_path, "wb") as f:
            content = await original_video.read()
            f.write(content)
            
        with open(ending_path, "wb") as f:
            content = await ending_video.read()
            f.write(content)
        
        logger.info(f"Saved files for session {session_id}")
        logger.info(f"Original: {original_path} ({original_path.stat().st_size} bytes)")
        logger.info(f"Ending: {ending_path} ({ending_path.stat().st_size} bytes)")
        
        # Merge videos
        success = merge_videos(original_path, ending_path, output_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to merge videos")
        
        logger.info(f"Successfully merged videos for session {session_id}")
        logger.info(f"Output: {output_path} ({output_path.stat().st_size} bytes)")
        
        # Return the merged video file
        return FileResponse(
            path=str(output_path),
            media_type="video/mp4",
            filename=f"merged_{platform}_{session_id}.mp4",
            headers={
                "X-Session-ID": session_id,
                "X-Platform": platform
            }
        )
        
    except Exception as e:
        logger.error(f"Error in merge_videos_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    finally:
        # Cleanup will happen in background, but we can schedule immediate cleanup
        # for this session after a delay
        pass

@app.post("/merge-videos-async")
async def merge_videos_async_endpoint(
    original_video: UploadFile = File(...),
    ending_video: UploadFile = File(...),
    platform: str = Form(...),
    callback_url: str = Form(None, description="Optional callback URL for completion notification")
):
    """
    Async version that returns a job ID immediately and processes in background
    """
    # This would require a background task queue like Celery
    # For now, just return the sync version
    return await merge_videos_endpoint(original_video, ending_video, platform)

@app.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Manually cleanup files for a specific session
    """
    session_dir = TEMP_DIR / session_id
    try:
        if session_dir.exists():
            shutil.rmtree(session_dir)
            return {"message": f"Session {session_id} cleaned up successfully"}
        else:
            return {"message": f"Session {session_id} not found"}
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup session: {str(e)}")

@app.get("/ffmpeg-info")
async def ffmpeg_info():
    """Get FFmpeg version and codec information"""
    if not check_ffmpeg():
        raise HTTPException(status_code=500, detail="FFmpeg is not available")
    
    try:
        # Get FFmpeg version
        version_result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Get available codecs
        codecs_result = subprocess.run(
            ["ffmpeg", "-codecs"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return {
            "version_info": version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "Error getting version",
            "codecs_available": "libx264" in codecs_result.stdout if codecs_result.returncode == 0 else False
        }
        
    except Exception as e:
        logger.error(f"Error getting FFmpeg info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting FFmpeg info: {str(e)}")

if __name__ == "__main__":
    # For development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )