import uuid
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse
from app.config.logging import get_logger

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Get logger with correlation context
        logger = get_logger(correlation_id=correlation_id)
        
        try:
            # Log request start
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params)
            )
            
            # Process request
            response = await call_next(request)
            
            # Log successful completion
            if response.status_code < 400:
                logger.info(
                    "request_completed",
                    status_code=response.status_code
                )
            else:
                # Log error response
                error_detail = "Not Found" if response.status_code == 404 else "Error response"
                if not isinstance(response, StreamingResponse):
                    try:
                        error_detail = getattr(response, 'body', error_detail)
                    except:
                        pass
                logger.error(
                    "request_failed",
                    error=error_detail,
                    status_code=response.status_code
                )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
            
        except HTTPException as e:
            # Log HTTP errors with "Not Found" message for 404s
            error_detail = "Not Found" if e.status_code == 404 else str(e.detail)
            logger.error(
                "request_failed",
                error=error_detail,
                status_code=e.status_code
            )
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(
                "request_failed",
                error=str(e),
                status_code=500,
                exc_info=True
            )
            raise HTTPException(status_code=500, detail=str(e)) 