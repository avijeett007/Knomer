"""
Storage service for video files using Supabase Storage
"""
import os
import logging
import tempfile
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from supabase import create_client, Client
from config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    """Storage service using Supabase Storage"""
    
    def __init__(self):
        # Only initialize Supabase if URL is provided
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            self.supabase: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            self.bucket_name = settings.STORAGE_BUCKET
            self._ensure_bucket_exists()
        else:
            self.supabase = None
            self.bucket_name = "local-storage"
            logger.warning("Supabase not configured, using local storage mode")
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        if not self.supabase:
            return

        try:
            # Try to get bucket info
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(bucket.name == self.bucket_name for bucket in buckets)

            if not bucket_exists:
                # Create bucket if it doesn't exist
                self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={"public": False}  # Private bucket
                )
                logger.info(f"Created storage bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {str(e)}")
    
    def upload_to_storage(self, file_path: Path, storage_path: str) -> Optional[str]:
        """
        Upload file to Supabase storage or local storage

        Args:
            file_path: Local file path
            storage_path: Path in storage bucket

        Returns:
            Public URL of uploaded file or None if failed
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            # If Supabase is not configured, return local file path
            if not self.supabase:
                logger.info(f"Local storage mode: file available at {file_path}")
                return f"file://{file_path.absolute()}"

            # Read file content
            with open(file_path, 'rb') as file:
                file_content = file.read()

            # Upload to Supabase storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={
                    "content-type": self._get_content_type(file_path),
                    "cache-control": "3600"
                }
            )

            if result:
                # Get public URL
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
                logger.info(f"Uploaded file to storage: {storage_path}")
                return public_url

            return None

        except Exception as e:
            logger.error(f"Error uploading to storage: {str(e)}")
            return None
    
    def download_from_storage(self, storage_path: str, local_path: Path) -> bool:
        """
        Download file from Supabase storage
        
        Args:
            storage_path: Path in storage bucket
            local_path: Local destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Download file content
            result = self.supabase.storage.from_(self.bucket_name).download(storage_path)
            
            if result:
                # Ensure directory exists
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to local file
                with open(local_path, 'wb') as file:
                    file.write(result)
                
                logger.info(f"Downloaded file from storage: {storage_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from storage: {str(e)}")
            return False
    
    def download_file(self, url: str, local_path: Path) -> bool:
        """
        Download file from external URL or copy from local file path

        Args:
            url: External URL or file:// URL
            local_path: Local destination path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle file:// URLs (local files)
            if url.startswith('file://'):
                source_path = Path(url.replace('file://', ''))
                if source_path.exists():
                    import shutil
                    shutil.copy2(source_path, local_path)
                    logger.info(f"Copied local file: {source_path} -> {local_path}")
                    return True
                else:
                    logger.error(f"Local file not found: {source_path}")
                    return False

            # Handle HTTP/HTTPS URLs
            # Download with streaming
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

            logger.info(f"Downloaded file from URL: {url}")
            return True

        except Exception as e:
            logger.error(f"Error downloading file from URL {url}: {str(e)}")
            return False
    
    def delete_file(self, storage_path_or_url: str) -> Optional[int]:
        """
        Delete file from storage
        
        Args:
            storage_path_or_url: Storage path or full URL
            
        Returns:
            File size that was deleted, or None if failed
        """
        try:
            # Extract storage path from URL if needed
            storage_path = self._extract_storage_path(storage_path_or_url)
            
            # Get file info before deletion
            try:
                file_info = self.supabase.storage.from_(self.bucket_name).info(storage_path)
                file_size = file_info.get('size', 0) if file_info else 0
            except:
                file_size = 0
            
            # Delete file
            result = self.supabase.storage.from_(self.bucket_name).remove([storage_path])
            
            if result:
                logger.info(f"Deleted file from storage: {storage_path}")
                return file_size
            
            return None
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return None
    
    def get_file_info(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from storage
        
        Args:
            storage_path: Path in storage bucket
            
        Returns:
            File info dict or None if failed
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).info(storage_path)
            return result
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create a signed URL for temporary access
        
        Args:
            storage_path: Path in storage bucket
            expires_in: Expiration time in seconds
            
        Returns:
            Signed URL or None if failed
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                storage_path,
                expires_in
            )
            
            if result:
                return result.get('signedURL')
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating signed URL: {str(e)}")
            return None
    
    def list_files(self, folder_path: str = "") -> List[Dict[str, Any]]:
        """
        List files in storage folder
        
        Args:
            folder_path: Folder path in bucket
            
        Returns:
            List of file info dicts
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).list(folder_path)
            return result or []
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics
        
        Returns:
            Storage usage info
        """
        try:
            # This would need to be implemented based on Supabase's storage API
            # For now, return basic info
            files = self.list_files()
            total_files = len(files)
            
            return {
                'total_files': total_files,
                'bucket_name': self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Error getting storage usage: {str(e)}")
            return {'total_files': 0, 'bucket_name': self.bucket_name}
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type based on file extension"""
        extension = file_path.suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _extract_storage_path(self, storage_path_or_url: str) -> str:
        """Extract storage path from URL or return path as-is"""
        if storage_path_or_url.startswith('http'):
            # Parse URL to extract path
            parsed = urlparse(storage_path_or_url)
            # Remove bucket name from path if present
            path_parts = parsed.path.strip('/').split('/')
            if path_parts[0] == self.bucket_name:
                return '/'.join(path_parts[1:])
            return '/'.join(path_parts)
        return storage_path_or_url
    
    def cleanup_temp_files(self, folder_path: str = "temp/") -> Dict[str, Any]:
        """
        Clean up temporary files older than threshold
        
        Args:
            folder_path: Temp folder path in bucket
            
        Returns:
            Cleanup results
        """
        try:
            files = self.list_files(folder_path)
            cleaned_count = 0
            total_size_freed = 0
            
            # This would need more sophisticated logic to check file ages
            # For now, just return basic info
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'size_freed_bytes': total_size_freed
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0,
                'size_freed_bytes': 0
            }
