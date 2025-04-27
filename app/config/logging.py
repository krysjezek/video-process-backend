import logging
import structlog
from typing import Any, Optional
from functools import lru_cache

def init_logging(logger_factory=None) -> None:
    """Initialize structured logging configuration."""
    # Reset any existing configuration
    structlog.reset_defaults()
    
    # Configure structlog with a simple logger factory
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=logger_factory or structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )

def get_logger(**kwargs: Any) -> structlog.BoundLogger:
    """Get a logger instance with optional context."""
    return structlog.get_logger().bind(**kwargs) 