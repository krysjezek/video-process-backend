from fastapi import HTTPException, status
from typing import Any, Dict

class APIError(HTTPException):
    """Base class for all API errors."""
    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        headers: Dict[str, str] | None = None
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"error_code": error_code, "detail": detail},
            headers=headers
        )

class TemplateNotFoundError(APIError):
    """Raised when a template ID doesn't exist."""
    def __init__(self, template_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="TEMPLATE_NOT_FOUND",
            detail=f"Template '{template_id}' does not exist"
        )

class VideoProcessingError(APIError):
    """Raised when video processing fails."""
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="VIDEO_PROCESSING_ERROR",
            detail=detail
        )

class StorageError(APIError):
    """Raised when storage operations fail."""
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="STORAGE_ERROR",
            detail=detail
        )

class ValidationError(APIError):
    """Raised when input validation fails."""
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            detail=detail
        ) 