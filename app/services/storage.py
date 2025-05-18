import os
from datetime import timedelta
from urllib.parse import urlparse
from minio import Minio
from app.config.logging import get_logger
from app.config.exceptions import StorageError

logger = get_logger(component="storage")


class MinioStorage:
    def __init__(self):
        # Internal client (I/O inside Docker)
        self._internal = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        self.bucket = os.getenv("MINIO_BUCKET", "video-mockups")
        self._ensure_bucket()

        # Public client (only for presign, never hits the wire)
        public_endpoint = "23.88.121.164:9000"  # Using direct IP
        logger.info(f"Using MinIO public endpoint: {public_endpoint}")
        
        self._public = Minio(
            public_endpoint,
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            region="us-east-1",
            secure=True,  # Enable HTTPS
        )

    def _ensure_bucket(self):
        if not self._internal.bucket_exists(self.bucket):
            self._internal.make_bucket(self.bucket)

    # ------------ uploads / downloads (unchanged) -------------
    def put_object(self, object_name: str, file_path: str) -> str:
        self._internal.fput_object(self.bucket, object_name, file_path)
        return object_name

    def get_object(self, object_name: str, file_path: str) -> None:
        self._internal.fget_object(self.bucket, object_name, file_path)

    def remove_object(self, object_name: str) -> None:
        self._internal.remove_object(self.bucket, object_name)

    # ------------ presigned URL (new) -------------
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        try:
            expires_td = timedelta(seconds=max(1, min(expires, 604800)))
            url = self._public.presigned_get_object(
                self.bucket, object_name, expires_td
            )
            logger.info(f"Generated presigned URL: {url}")
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

# Create and export a single instance of MinioStorage
storage = MinioStorage()
