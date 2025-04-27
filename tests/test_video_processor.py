import pytest
from app.services.scene_processor import process_scene_with_effect_chain
from app.config import load_mockup_config

def test_process_video(mock_video_path, mock_output_path, mock_scene_config):
    """Test that a video can be processed successfully."""
    # Process the video
    process_scene_with_effect_chain(
        mockup_config=mock_scene_config,
        user_video_path=mock_video_path,
        scene_timing={"in_frame": 0, "out_frame": 24},  # 1 second at 24fps
        output_path=mock_output_path,
        user_video_offset=0.0
    )
    
    # Verify the output file exists
    assert mock_output_path.exists()
    
    # Verify the output file is a video
    assert mock_output_path.suffix in [".mp4", ".mov"]
    
    # Verify the output file is not empty
    assert mock_output_path.stat().st_size > 0

def test_invalid_video_path(mock_output_path, mock_scene_config):
    """Test that an invalid video path raises an error."""
    with pytest.raises(IOError):
        process_scene_with_effect_chain(
            mockup_config=mock_scene_config,
            user_video_path="invalid/path/to/video.mp4",
            scene_timing={"in_frame": 0, "out_frame": 24},
            output_path=mock_output_path,
            user_video_offset=0.0
        )

def test_invalid_scene_timing(mock_video_path, mock_output_path, mock_scene_config):
    """Test that invalid scene timing raises an error."""
    with pytest.raises(ValueError):
        process_scene_with_effect_chain(
            mockup_config=mock_scene_config,
            user_video_path=mock_video_path,
            scene_timing={"in_frame": 100, "out_frame": 0},  # Invalid timing
            output_path=mock_output_path,
            user_video_offset=0.0
        ) 