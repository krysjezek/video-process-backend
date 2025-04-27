import pytest
import os
import tempfile
import numpy as np
import moviepy.editor as mpy
from app.services.timeline_assembler import assemble_timeline

@pytest.fixture
def temp_video_files():
    """Create temporary video files for testing."""
    temp_dir = tempfile.mkdtemp()
    video_paths = []
    
    # Create 3 test videos with different durations
    for i in range(3):
        # Create a simple color frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, i] = 255  # Different color for each video
        
        # Create a clip with duration and write to file
        clip = mpy.ImageClip(frame).set_duration(1.0)  # 1 second duration
        path = os.path.join(temp_dir, f"test_video_{i}.mp4")
        clip.write_videofile(path, fps=24, codec="libx264", audio_codec="aac")
        video_paths.append(path)
    
    yield video_paths
    
    # Cleanup
    for path in video_paths:
        if os.path.exists(path):
            os.remove(path)
    os.rmdir(temp_dir)

def test_basic_concatenation(temp_video_files):
    """Test basic video concatenation functionality."""
    output_path = os.path.join(tempfile.gettempdir(), "output_test.mp4")
    
    try:
        # Assemble timeline
        assemble_timeline(temp_video_files, output_path)
        
        # Verify output exists
        assert os.path.exists(output_path)
        
        # Verify output video properties
        output_clip = mpy.VideoFileClip(output_path)
        assert tuple(output_clip.size) == (640, 480)  # Convert list to tuple for comparison
        assert output_clip.fps == 24
        assert output_clip.duration == sum(mpy.VideoFileClip(fp).duration for fp in temp_video_files)
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

def test_nonexistent_input_files():
    """Test handling of nonexistent input files."""
    with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_output:
        with pytest.raises(FileNotFoundError):
            assemble_timeline(["nonexistent1.mp4", "nonexistent2.mp4"], temp_output.name)

def test_output_directory_creation(temp_video_files):
    """Test that output directory is created if it doesn't exist."""
    output_dir = os.path.join(tempfile.gettempdir(), "test_output_dir")
    output_path = os.path.join(output_dir, "output_test.mp4")
    
    try:
        # Directory shouldn't exist initially
        assert not os.path.exists(output_dir)
        
        # Assemble timeline
        assemble_timeline(temp_video_files, output_path)
        
        # Verify directory was created
        assert os.path.exists(output_dir)
        assert os.path.exists(output_path)
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
        if os.path.exists(output_dir):
            os.rmdir(output_dir)

def test_different_resolutions(temp_video_files):
    """Test handling of videos with different resolutions."""
    # Create a video with different resolution
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    clip = mpy.ImageClip(frame).set_duration(1.0)  # 1 second duration
    different_res_path = os.path.join(os.path.dirname(temp_video_files[0]), "different_res.mp4")
    clip.write_videofile(different_res_path, fps=24, codec="libx264", audio_codec="aac")
    
    output_path = os.path.join(tempfile.gettempdir(), "output_test.mp4")
    
    try:
        # Should raise ValueError due to resolution mismatch
        with pytest.raises(ValueError):
            assemble_timeline(temp_video_files + [different_res_path], output_path)
            
    finally:
        if os.path.exists(different_res_path):
            os.remove(different_res_path)
        if os.path.exists(output_path):
            os.remove(output_path)

def test_audio_handling(temp_video_files):
    """Test that audio is properly handled in concatenation."""
    # Create a video with audio
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create audio clip with a function that returns the audio data
    def make_audio(t):
        return np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
    
    clip = mpy.ImageClip(frame).set_duration(1.0)  # 1 second duration
    audio_clip = mpy.AudioClip(make_audio, duration=1.0, fps=44100)
    clip = clip.set_audio(audio_clip)
    
    audio_path = os.path.join(os.path.dirname(temp_video_files[0]), "audio_test.mp4")
    clip.write_videofile(audio_path, fps=24, codec="libx264", audio_codec="aac")
    
    output_path = os.path.join(tempfile.gettempdir(), "output_test.mp4")
    
    try:
        # Assemble timeline with audio video
        assemble_timeline(temp_video_files + [audio_path], output_path)
        
        # Verify output has audio
        output_clip = mpy.VideoFileClip(output_path)
        assert output_clip.audio is not None
        
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(output_path):
            os.remove(output_path) 