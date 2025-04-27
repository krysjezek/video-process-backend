import pytest
from fastapi import status
from app.config.exceptions import TemplateNotFoundError

def test_health_check(client, setup_logging):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}
    
    # Verify logging
    log_content = setup_logging.getvalue()
    assert "request_started" in log_content
    assert "request_completed" in log_content
    assert "status_code=200" in log_content

def test_correlation_id_propagation(client, setup_logging):
    """Test that correlation IDs are properly propagated."""
    correlation_id = "test-correlation-123"
    response = client.get(
        "/health",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    # Verify correlation ID in response
    assert response.headers["X-Correlation-ID"] == correlation_id
    
    # Verify correlation ID in logs
    log_content = setup_logging.getvalue()
    assert f"correlation_id={correlation_id}" in log_content

def test_error_handling(client, setup_logging):
    """Test error handling and logging."""
    # Test with invalid template ID
    response = client.get("/api/templates/invalid-template")
    
    # Verify error response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Not Found"
    
    # Verify error logging
    log_content = setup_logging.getvalue()
    assert "request_failed" in log_content
    assert "status_code=404" in log_content 