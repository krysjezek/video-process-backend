from app.config.logging import init_logging, get_logger

def test_logging():
    # Initialize logging
    init_logging()
    
    # Get different logger instances
    logger = get_logger()
    logger_with_context = get_logger(component="test", action="logging")
    
    # Test basic logging
    logger.info("Basic log message")
    
    # Test logging with context
    logger_with_context.info("Log with context")
    
    # Test logging with additional context
    logger.info("Log with extra context", extra_field="value")
    
    # Test different log levels
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test nested context
    nested_logger = logger_with_context.bind(nested="true")
    nested_logger.info("Nested context log")

if __name__ == "__main__":
    test_logging() 