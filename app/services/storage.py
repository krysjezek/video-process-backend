import os
from datetime import timedelta

from minio import Minio
from app.config.logging import get_logger
from app.config.exceptions import StorageError

logger = get_logger(component="storage")


class MinioStorage:
    """
    Wraps MinIO access.

    * _internal — talks to MinIO over the Docker network (plain HTTP)
    * _public   — only generates presigned *HTTPS* URLs for the browser
    """

    def __init__(self):
        # ── Internal client (inside the compose network) ────────────────────────
        self._internal = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,                        # container-to-container = HTTP
        )

        self.bucket = os.getenv("MINIO_BUCKET", "video-mockups")
        self._ensure_bucket()

        # ── Public client: never sends traffic, only builds presigned URLs ─────
        public_endpoint = "files.23-88-121-164.nip.io"   # HTTPS host served by Caddy
        logger.info(f"Using MinIO public endpoint: {public_endpoint}")

        self._public = Minio(
            public_endpoint,
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            region="us-east-1",
            secure=True,                         # <- HTTPS fixes mixed-content
        )

    def _ensure_bucket(self):
        if not self._internal.bucket_exists(self.bucket):
            self._internal.make_bucket(self.bucket)

    # ── Upload / download helpers ───────────────────────────────────────────────
    def put_object(self, object_name: str, file_path: str) -> str:
        self._internal.fput_object(self.bucket, object_name, file_path)
        return object_name

    def get_object(self, object_name: str, file_path: str) -> None:
        self._internal.fget_object(self.bucket, object_name, file_path)

    def remove_object(self, object_name: str) -> None:
        self._internal.remove_object(self.bucket, object_name)

    # ── Generate presigned HTTPS URL for the front-end ─────────────────────────
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        try:
            expires_td = timedelta(seconds=max(1, min(expires, 604_800)))
            url = self._public.presigned_get_object(
                self.bucket, object_name, expires_td
            )
            logger.info(f"Generated presigned URL: {url}")
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")


# Single, shared instance
storage = MinioStorage()
