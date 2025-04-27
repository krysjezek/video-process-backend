# tests/conftest.py
import sys, os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.logging import init_logging
import structlog
import io
import json
import logging
from pathlib import Path
import tempfile
import subprocess

# insert the project root (one directory up) onto Python's import path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app.tasks.celery_app import celery_app

@pytest.fixture(autouse=True, scope="session")
def celery_eager():
    celery_app.conf.update(task_always_eager=True)
    yield

@pytest.fixture
def setup_logging():
    """Set up logging for tests."""
    # Create a StringIO stream to capture logs
    log_stream = io.StringIO()
    
    # Custom processor to format logs in a way that matches our test assertions
    def format_for_test(logger, name, event_dict):
        # Format the output as JSON with specific formatting
        output = [f'"event": "{event_dict.get("event", "unknown")}"']
        for key, value in sorted(event_dict.items()):
            if key not in ["event", "timestamp", "level"]:  # Skip processed fields
                # Handle different value types
                if isinstance(value, (int, float)):
                    output.append(f'"{key}": {value}')  # No quotes for numbers
                else:
                    # Remove any quotes from the value and escape existing quotes
                    value = str(value).strip("'").replace('"', '\\"')
                    output.append(f'"{key}": "{value}"')
        return "{" + ", ".join(output) + "}\n"  # Add newline for better readability
    
    # Create a custom logger factory that writes to our stream
    class StringIOLoggerFactory:
        def __init__(self, stream):
            self.stream = stream
        
        def __call__(self, *args):
            return structlog.PrintLogger(file=self.stream)
    
    # Reset any existing configuration
    structlog.reset_defaults()
    
    # Configure structlog with our test configuration
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            format_for_test
        ],
        logger_factory=StringIOLoggerFactory(log_stream),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True
    )
    
    # Initialize application logging with our custom logger factory
    init_logging(logger_factory=StringIOLoggerFactory(log_stream))
    
    yield log_stream
    
    # Clean up
    log_stream.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_job_id():
    """Return a mock job ID for testing."""
    return "test-job-123"

@pytest.fixture
def mock_template_id():
    """Return a valid template ID for testing."""
    return "mockup1"

@pytest.fixture
def mock_video_path(tmp_path):
    """Create a temporary test video file using ffmpeg."""
    video_path = tmp_path / "test_video.mp4"
    # Create a 1-second black video
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1280x720:d=1",
        "-c:v", "libx264",
        str(video_path)
    ], check=True)
    return video_path

@pytest.fixture
def mock_output_path(tmp_path):
    """Create a temporary output path for testing."""
    return tmp_path / "output.mp4"

@pytest.fixture
def mock_scene_config():
    """Return a mock scene configuration."""
    return {
        "scene_id": "scene1",
        "assets": {
            "background": None,  # We'll test without background for simplicity
            "corner_pin_data": None
        },
        "default_effects_chain": [
            {
                "effect": "corner_pin",
                "params": {
                    "use_mask": True,
                    "corner_pin_data": {
                        "0": {
                            "ul": [0, 0],
                            "ur": [1280, 0],
                            "ll": [0, 720],
                            "lr": [1280, 720]
                        }
                    }
                }
            }
        ]
    }

def parse_log_line(log_line: str) -> dict:
    """Parse a JSON log line into a dictionary."""
    return json.loads(log_line)

