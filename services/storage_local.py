"""
Local file system storage service for testing
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

class LocalStorageService:
    """Local file system storage service"""
    
    def __init__(self, base_path: str = "./temp/storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_path}")
    
    def upload_to_storage(self, file_path: Path, storage_path: str) -> Optional[str]:
        """
        Upload file to local storage
        
        Args:
            file_path: Local file path
            storage_path: Path in storage
            
        Returns:
            Local file URL or None if failed
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Create destination path
            dest_path = self.base_path / storage_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(file_path, dest_path)
            
            # Return local file URL
            local_url = f"file://{dest_path.absolute()}"
            logger.info(f"Uploaded file to local storage: {storage_path}")
            return local_url
            
        except Exception as e:
            logger.error(f"Error uploading to local storage: {e}")
            return None
    
    def download_from_storage(self, storage_path: str, local_path: Path) -> bool:
        """
        Download file from local storage
        
        Args:
            storage_path: Path in storage
            local_path: Local destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = self.base_path / storage_path
            
            if not source_path.exists():
                logger.error(f"Storage file not found: {source_path}")
                return False
            
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, local_path)
            
            logger.info(f"Downloaded file from local storage: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading from local storage: {e}")
            return False
    
    def download_file(self, url: str, local_path: Path) -> bool:
        """
        Download file from URL (external or local)
        
        Args:
            url: File URL
            local_path: Local destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if url.startswith('file://'):
                # Local file URL
                source_path = Path(url.replace('file://', ''))
                if source_path.exists():
                    shutil.copy2(source_path, local_path)
                    logger.info(f"Copied local file: {url}")
                    return True
                else:
                    logger.error(f"Local file not found: {source_path}")
                    return False
            else:
                # External URL - download with requests
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()
                
                with open(local_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                
                logger.info(f"Downloaded file from URL: {url}")
                return True
                
        except Exception as e:
            logger.error(f"Error downloading file from URL {url}: {e}")
            return False
    
    def delete_file(self, storage_path_or_url: str) -> Optional[int]:
        """
        Delete file from storage
        
        Args:
            storage_path_or_url: Storage path or file URL
            
        Returns:
            File size that was deleted, or None if failed
        """
        try:
            # Extract storage path from URL if needed
            if storage_path_or_url.startswith('file://'):
                file_path = Path(storage_path_or_url.replace('file://', ''))
            else:
                file_path = self.base_path / storage_path_or_url
            
            if not file_path.exists():
                logger.warning(f"File not found for deletion: {file_path}")
                return None
            
            # Get file size before deletion
            file_size = file_path.stat().st_size
            
            # Delete file
            file_path.unlink()
            
            logger.info(f"Deleted file from local storage: {file_path}")
            return file_size
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return None
    
    def get_file_info(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from storage
        
        Args:
            storage_path: Path in storage
            
        Returns:
            File info dict or None if failed
        """
        try:
            file_path = self.base_path / storage_path
            
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'created_at': stat.st_ctime,
                'modified_at': stat.st_mtime,
                'path': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create a signed URL for temporary access (for local storage, just return file URL)
        
        Args:
            storage_path: Path in storage
            expires_in: Expiration time in seconds (ignored for local storage)
            
        Returns:
            File URL or None if failed
        """
        try:
            file_path = self.base_path / storage_path
            
            if not file_path.exists():
                return None
            
            return f"file://{file_path.absolute()}"
            
        except Exception as e:
            logger.error(f"Error creating signed URL: {e}")
            return None
    
    def list_files(self, folder_path: str = "") -> List[Dict[str, Any]]:
        """
        List files in storage folder
        
        Args:
            folder_path: Folder path in storage
            
        Returns:
            List of file info dicts
        """
        try:
            search_path = self.base_path / folder_path if folder_path else self.base_path
            
            if not search_path.exists():
                return []
            
            files = []
            for file_path in search_path.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        'name': file_path.name,
                        'size': stat.st_size,
                        'created_at': stat.st_ctime,
                        'modified_at': stat.st_mtime,
                        'path': str(file_path.relative_to(self.base_path))
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics
        
        Returns:
            Storage usage info
        """
        try:
            total_size = 0
            total_files = 0
            
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    total_files += 1
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'base_path': str(self.base_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return {'total_files': 0, 'total_size_bytes': 0, 'total_size_mb': 0}
    
    def cleanup_temp_files(self, folder_path: str = "temp/") -> Dict[str, Any]:
        """
        Clean up temporary files
        
        Args:
            folder_path: Temp folder path in storage
            
        Returns:
            Cleanup results
        """
        try:
            temp_path = self.base_path / folder_path
            
            if not temp_path.exists():
                return {
                    'success': True,
                    'cleaned_count': 0,
                    'size_freed_bytes': 0
                }
            
            cleaned_count = 0
            total_size_freed = 0
            
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_count += 1
                    total_size_freed += file_size
            
            # Remove empty directories
            for dir_path in temp_path.rglob('*'):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'size_freed_bytes': total_size_freed
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0,
                'size_freed_bytes': 0
            }
