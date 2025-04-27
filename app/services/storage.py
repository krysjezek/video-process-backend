from minio import Minio
from minio.error import S3Error
import os
from typing import Optional
from datetime import timedelta
from app.config.logging import get_logger
from app.config.exceptions import StorageError

logger = get_logger(component="storage")

class MinioStorage:
    def __init__(self):
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False  # Set to True in production with proper TLS
        )
        self.bucket = os.getenv("MINIO_BUCKET", "video-mockups")
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            logger.error("Failed to ensure bucket exists", error=str(e))
            raise StorageError(f"Failed to ensure bucket exists: {str(e)}")

    def put_object(self, object_name: str, file_path: str) -> str:
        """Upload a file to MinIO and return the object name."""
        try:
            self.client.fput_object(
                self.bucket,
                object_name,
                file_path
            )
            return object_name
        except S3Error as e:
            logger.error("Failed to upload object", error=str(e))
            raise StorageError(f"Failed to upload object: {str(e)}")

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned URL for downloading an object."""
        try:
            # Ensure expires is a positive integer
            expires = max(1, min(expires, 604800))  # MinIO limits: 1s to 7 days
            # Convert to timedelta
            expires_td = timedelta(seconds=expires)
            return self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires_td
            )
        except S3Error as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

    def get_object(self, object_name: str, file_path: str) -> None:
        """Download an object from MinIO to a local file."""
        try:
            self.client.fget_object(
                self.bucket,
                object_name,
                file_path
            )
        except S3Error as e:
            logger.error("Failed to download object", error=str(e))
            raise StorageError(f"Failed to download object: {str(e)}")

    def remove_object(self, object_name: str) -> None:
        """Remove an object from MinIO."""
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error as e:
            logger.error("Failed to remove object", error=str(e))
            raise StorageError(f"Failed to remove object: {str(e)}")

# Create a singleton instance
storage = MinioStorage() 