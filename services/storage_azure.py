"""
Azure Blob Storage service for video processing API
"""
import logging
from pathlib import Path
from typing import Optional
import requests
from urllib.parse import urlparse

try:
    from azure.storage.blob import BlobServiceClient, BlobClient
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from config.settings import settings

logger = logging.getLogger(__name__)

class AzureStorageService:
    """Azure Blob Storage service"""
    
    def __init__(self):
        if not AZURE_AVAILABLE:
            raise ImportError("Azure Storage SDK not installed. Run: pip install azure-storage-blob")
        
        if not settings.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING not configured")
        
        self.blob_service = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = settings.STORAGE_BUCKET
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure the storage container exists"""
        try:
            # Try to get container properties
            self.blob_service.get_container_client(self.container_name).get_container_properties()
            logger.info(f"Using existing container: {self.container_name}")
        except ResourceNotFoundError:
            # Create container if it doesn't exist
            try:
                self.blob_service.create_container(
                    self.container_name,
                    public_access='blob'  # Allow public read access to blobs
                )
                logger.info(f"Created storage container: {self.container_name}")
            except Exception as e:
                logger.error(f"Error creating container: {str(e)}")
                raise
    
    def upload_to_storage(self, file_path: Path, storage_path: str) -> Optional[str]:
        """
        Upload file to Azure Blob Storage
        
        Args:
            file_path: Local file path
            storage_path: Path in storage container
            
        Returns:
            Public URL of uploaded file or None if failed
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Get blob client
            blob_client = self.blob_service.get_blob_client(
                container=self.container_name,
                blob=storage_path
            )
            
            # Upload file
            with open(file_path, 'rb') as file:
                blob_client.upload_blob(
                    file,
                    overwrite=True,
                    content_settings={
                        'content_type': self._get_content_type(file_path),
                        'cache_control': 'max-age=3600'
                    }
                )
            
            # Return public URL
            public_url = blob_client.url
            logger.info(f"Uploaded file to Azure Storage: {storage_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading to Azure Storage: {str(e)}")
            return None
    
    def download_from_storage(self, storage_path: str, local_path: Path) -> bool:
        """
        Download file from Azure Blob Storage
        
        Args:
            storage_path: Path in storage container
            local_path: Local destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get blob client
            blob_client = self.blob_service.get_blob_client(
                container=self.container_name,
                blob=storage_path
            )
            
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            with open(local_path, 'wb') as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())
            
            logger.info(f"Downloaded file from Azure Storage: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading from Azure Storage: {str(e)}")
            return False
    
    def download_from_url(self, url: str, local_path: Path) -> bool:
        """
        Download file from URL to local path
        
        Args:
            url: File URL
            local_path: Local destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle Azure blob URLs
            if 'blob.core.windows.net' in url:
                # Extract container and blob name from URL
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    container_name = path_parts[0]
                    blob_name = '/'.join(path_parts[1:])
                    
                    blob_client = self.blob_service.get_blob_client(
                        container=container_name,
                        blob=blob_name
                    )
                    
                    with open(local_path, 'wb') as file:
                        download_stream = blob_client.download_blob()
                        file.write(download_stream.readall())
                    
                    logger.info(f"Downloaded Azure blob: {url}")
                    return True
            
            # Handle regular HTTP/HTTPS URLs
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            
            logger.info(f"Downloaded file from URL: {url}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading from URL: {str(e)}")
            return False
    
    def delete_file(self, storage_path_or_url: str) -> Optional[int]:
        """
        Delete file from Azure Blob Storage
        
        Args:
            storage_path_or_url: Storage path or full URL
            
        Returns:
            File size that was deleted, or None if failed
        """
        try:
            # Extract storage path from URL if needed
            storage_path = self._extract_storage_path(storage_path_or_url)
            
            # Get blob client
            blob_client = self.blob_service.get_blob_client(
                container=self.container_name,
                blob=storage_path
            )
            
            # Get file size before deletion
            try:
                properties = blob_client.get_blob_properties()
                file_size = properties.size
            except:
                file_size = 0
            
            # Delete blob
            blob_client.delete_blob()
            
            logger.info(f"Deleted file from Azure Storage: {storage_path}")
            return file_size
            
        except Exception as e:
            logger.error(f"Error deleting from Azure Storage: {str(e)}")
            return None
    
    def _extract_storage_path(self, storage_path_or_url: str) -> str:
        """Extract storage path from URL or return path as-is"""
        if storage_path_or_url.startswith('http'):
            # Extract path from URL
            parsed_url = urlparse(storage_path_or_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return '/'.join(path_parts[1:])  # Skip container name
        return storage_path_or_url
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type based on file extension"""
        extension = file_path.suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create a signed URL for temporary access
        
        Args:
            storage_path: Path in storage container
            expires_in: Expiration time in seconds
            
        Returns:
            Signed URL or None if failed
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import datetime, timedelta
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service.account_name,
                container_name=self.container_name,
                blob_name=storage_path,
                account_key=self.blob_service.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            
            # Get blob client and create signed URL
            blob_client = self.blob_service.get_blob_client(
                container=self.container_name,
                blob=storage_path
            )
            
            signed_url = f"{blob_client.url}?{sas_token}"
            return signed_url
            
        except Exception as e:
            logger.error(f"Error creating signed URL: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "") -> list:
        """
        List files in storage container
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths
        """
        try:
            container_client = self.blob_service.get_container_client(self.container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            
            return [blob.name for blob in blobs]
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
