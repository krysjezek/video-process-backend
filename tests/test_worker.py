import pytest
from app.tasks.processing_tasks import process_video
from app.config.exceptions import VideoProcessingError
import json
import os
import tempfile
import sys
from io import StringIO

def test_video_processing_success(capsys, mock_job_id, mock_template_id, mock_video_path):
    """Test successful video processing."""
    # Create a temporary mockup config
    data = {
        mock_template_id: {
            "scenes": [
                {
                    "scene_id": "scene1",
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
            ]
        }
    }
    config_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    config_file.write(json.dumps(data))
    config_file.close()
    
    # Set the config path
    os.environ["MOCKUPS_PATH"] = config_file.name
    
    # Mock video path
    video_path = str(mock_video_path)
    
    try:
        # Run the task
        result = process_video(mock_job_id, mock_template_id, video_path)
        
        # Verify result
        assert result["status"] == "success"
        assert result["job_id"] == mock_job_id
        
        # Get captured output
        captured = capsys.readouterr()
        log_content = captured.out + captured.err
        
        # Verify logging
        assert "starting_video_processing" in log_content
        assert "video_processing_completed" in log_content
        assert f"job_id={mock_job_id}" in log_content
    finally:
        # Clean up
        os.unlink(config_file.name)

def test_video_processing_error(capsys, mock_job_id, mock_template_id):
    """Test video processing error handling."""
    # Mock invalid video path
    video_path = "invalid.mp4"
    
    # Verify error is raised
    with pytest.raises(VideoProcessingError):
        process_video(mock_job_id, mock_template_id, video_path)
    
    # Get captured output
    captured = capsys.readouterr()
    log_content = captured.out + captured.err
    
    # Verify error logging
    assert "video_processing_failed" in log_content
    assert "error=" in log_content 