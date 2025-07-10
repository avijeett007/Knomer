"""
Hybrid storage service for video processing API
Uses local storage for processing and Supabase for output storage
"""
import logging
import shutil
from pathlib import Path
from typing import Optional
import requests
from urllib.parse import urlparse

from config.settings import settings

# Import storage services
try:
    from services.storage import StorageService as SupabaseStorageService
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from services.storage_local import LocalStorageService

logger = logging.getLogger(__name__)

class HybridStorageService:
    """
    Hybrid storage service that uses:
    - Local storage for temporary processing files
    - Supabase storage for permanent output files
    """
    
    def __init__(self):
        # Initialize local storage for processing
        self.local_storage = LocalStorageService()
        
        # Initialize Supabase storage for output (if available)
        if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            self.cloud_storage = SupabaseStorageService()
            self.use_cloud_output = True
            logger.info("Hybrid storage: Local processing + Supabase output")
        else:
            self.cloud_storage = self.local_storage
            self.use_cloud_output = False
            logger.warning("Hybrid storage: Local only (Supabase not configured)")
    
    def upload_temp_file(self, file_path: Path, temp_path: str) -> Optional[str]:
        """
        Upload file to temporary local storage for processing
        
        Args:
            file_path: Source file path
            temp_path: Temporary storage path
            
        Returns:
            Local file URL for processing
        """
        try:
            # Always use local storage for temp files
            return self.local_storage.upload_to_storage(file_path, f"temp/{temp_path}")
        except Exception as e:
            logger.error(f"Error uploading temp file: {e}")
            return None
    
    def upload_output_file(self, file_path: Path, output_path: str) -> Optional[str]:
        """
        Upload processed file to permanent storage (Supabase or local)
        
        Args:
            file_path: Processed file path
            output_path: Permanent storage path
            
        Returns:
            Public URL of uploaded file
        """
        try:
            if self.use_cloud_output:
                # Upload to Supabase for permanent storage
                return self.cloud_storage.upload_to_storage(file_path, f"outputs/{output_path}")
            else:
                # Fallback to local storage
                return self.local_storage.upload_to_storage(file_path, f"outputs/{output_path}")
        except Exception as e:
            logger.error(f"Error uploading output file: {e}")
            return None
    
    def upload_to_storage(self, file_path: Path, storage_path: str) -> Optional[str]:
        """
        Main upload method - routes to appropriate storage based on path
        
        Args:
            file_path: Source file path
            storage_path: Storage path (determines temp vs output)
            
        Returns:
            Storage URL
        """
        if storage_path.startswith('temp/') or storage_path.startswith('processing/'):
            return self.upload_temp_file(file_path, storage_path)
        else:
            return self.upload_output_file(file_path, storage_path)
            
    def get_public_url(self, storage_path: str) -> Optional[str]:
        """
        Get public URL for a file in storage
        
        Args:
            storage_path: Path in storage (e.g. outputs/file.mp4)
            
        Returns:
            Public URL to the file if available, None otherwise
        """
        try:
            if self.use_cloud_output:
                # For cloud storage, get the URL from the cloud provider
                return self.cloud_storage.get_public_url(storage_path)
            else:
                # For local storage, use SERVER_URL environment variable
                from urllib.parse import urljoin
                filename = os.path.basename(storage_path)
                return urljoin(settings.SERVER_URL, f"/api/v1/download/{filename}")
        except Exception as e:
            logger.error(f"Error getting public URL for {storage_path}: {str(e)}")
            return None
    
    async def download_from_url(self, url: str, target_path: Path) -> Optional[Path]:
        """
        Download file from public URL (S3, Supabase, etc.) to local path
        
        Args:
            url: Public URL to download from
            target_path: Local file path to save to
            
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        try:
            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file with requests
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Verify download was successful
            if target_path.exists() and target_path.stat().st_size > 0:
                logger.info(f"Successfully downloaded {url} to {target_path}")
                return target_path
            else:
                logger.error(f"Failed to download {url}: Empty file")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading from URL {url}: {str(e)}")
            return None
    
    def download_from_storage(self, storage_path: str, local_path: Path) -> bool:
        """
        Download file from storage (checks both local and cloud)
        
        Args:
            storage_path: Storage path
            local_path: Local destination path
            
        Returns:
            True if successful
        """
        try:
            # Try cloud storage first for output files
            if self.use_cloud_output and not storage_path.startswith('temp/'):
                if self.cloud_storage.download_from_storage(storage_path, local_path):
                    return True
            
            # Fallback to local storage
            return self.local_storage.download_from_storage(storage_path, local_path)
            
        except Exception as e:
            logger.error(f"Error downloading from storage: {e}")
            return False
    
    def download_from_url(self, url: str, local_path: Path) -> bool:
        """
        Download file from URL to local path
        
        Args:
            url: File URL (can be local file:// or HTTP/HTTPS)
            local_path: Local destination path
            
        Returns:
            True if successful
        """
        try:
            # Handle Supabase URLs
            if self.use_cloud_output and 'supabase' in url:
                return self.cloud_storage.download_from_url(url, local_path)
            
            # Handle local file URLs
            if url.startswith('file://'):
                return self.local_storage.download_from_url(url, local_path)
            
            # Handle HTTP/HTTPS URLs
            local_path.parent.mkdir(parents=True, exist_ok=True)
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            
            logger.info(f"Downloaded file from URL: {url}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading from URL: {e}")
            return False
    
    def delete_file(self, storage_path_or_url: str) -> Optional[int]:
        """
        Delete file from storage
        
        Args:
            storage_path_or_url: Storage path or URL
            
        Returns:
            File size deleted or None if failed
        """
        try:
            # Try cloud storage first for output files
            if self.use_cloud_output and not storage_path_or_url.startswith('temp/'):
                result = self.cloud_storage.delete_file(storage_path_or_url)
                if result is not None:
                    return result
            
            # Fallback to local storage
            return self.local_storage.delete_file(storage_path_or_url)
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_hours: int = 2) -> int:
        """
        Clean up temporary processing files older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours for temp files
            
        Returns:
            Number of files cleaned up
        """
        try:
            temp_dir = Path(settings.LOCAL_STORAGE_PATH) / "temp"
            if not temp_dir.exists():
                return 0
            
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.debug(f"Cleaned up temp file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
            # Clean up empty directories
            for dir_path in temp_dir.rglob("*"):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    try:
                        dir_path.rmdir()
                    except:
                        pass
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} temporary files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage stats
        """
        stats = {
            "local_storage": self.local_storage.get_storage_stats() if hasattr(self.local_storage, 'get_storage_stats') else {},
            "cloud_storage_enabled": self.use_cloud_output,
            "temp_files_count": 0,
            "temp_files_size": 0
        }
        
        try:
            temp_dir = Path(settings.LOCAL_STORAGE_PATH) / "temp"
            if temp_dir.exists():
                temp_files = list(temp_dir.rglob("*"))
                stats["temp_files_count"] = len([f for f in temp_files if f.is_file()])
                stats["temp_files_size"] = sum(f.stat().st_size for f in temp_files if f.is_file())
        except:
            pass
        
        return stats
    
    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create signed URL for file access
        
        Args:
            storage_path: Storage path
            expires_in: Expiration time in seconds
            
        Returns:
            Signed URL or None if failed
        """
        try:
            # Use cloud storage for output files if available
            if self.use_cloud_output and not storage_path.startswith('temp/'):
                return self.cloud_storage.create_signed_url(storage_path, expires_in)
            
            # Fallback to local storage
            return self.local_storage.create_signed_url(storage_path, expires_in)
            
        except Exception as e:
            logger.error(f"Error creating signed URL: {e}")
            return None
