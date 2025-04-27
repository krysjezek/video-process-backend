import pytest
import numpy as np
import json
import cv2
from app.services.effects.perspective_transformations import (
    apply_corner_pin,
    load_corner_pin_data,
    corner_pin_effect
)

@pytest.fixture
def sample_frame():
    """Create a sample frame for testing with a more complex pattern."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Create a checkerboard pattern in the center
    frame[25:75, 25:75, :] = 255  # White square
    frame[25:50, 25:50, :] = 0    # Black top-left quadrant
    frame[50:75, 50:75, :] = 0    # Black bottom-right quadrant
    return frame

@pytest.fixture
def sample_corners():
    """Create sample corner points for testing."""
    return {
        'ul': [0, 0],
        'ur': [100, 0],
        'lr': [100, 100],
        'll': [0, 100]
    }

@pytest.fixture
def transformed_corners():
    """Create transformed corner points for testing with a more significant transformation."""
    return {
        'ul': [20, 20],    # Shifted up and left
        'ur': [80, 20],    # Shifted up and right
        'lr': [100, 100],  # Kept at original position
        'll': [0, 100]     # Kept at original position
    }

@pytest.fixture
def mock_user_clip():
    """Create a mock MoviePy clip for testing with a more complex pattern."""
    class MockClip:
        def __init__(self, duration=1.0):
            self.duration = duration
            
        def get_frame(self, t):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            if t < self.duration:
                # Create a diagonal pattern
                for i in range(100):
                    for j in range(100):
                        if i + j < 100:
                            frame[i, j, :] = 255
            return frame
    return MockClip()

@pytest.fixture
def mock_corner_pin_data():
    """Create mock corner pin tracking data with more significant transformations."""
    return {
        "0": {
            "ul": [0, 0],
            "ur": [100, 0],
            "lr": [100, 100],
            "ll": [0, 100]
        },
        "1": {
            "ul": [20, 20],
            "ur": [80, 20],
            "lr": [100, 100],
            "ll": [0, 100]
        }
    }

def test_apply_corner_pin_basic(sample_frame, transformed_corners):
    """Test basic corner pin transformation."""
    output_size = (100, 100)
    warped = apply_corner_pin(sample_frame, transformed_corners, output_size)
    
    # Verify output shape and type
    assert warped.shape == (output_size[1], output_size[0], 3)
    assert warped.dtype == np.uint8
    
    # Verify that transformation occurred by checking specific regions
    # Check the original white region
    original_white = sample_frame[25:75, 25:75, :]
    warped_white = warped[25:75, 25:75, :]
    
    # The transformation should have moved the white region
    assert not np.array_equal(original_white, warped_white)
    
    # Verify that the transformation preserved the pattern
    # Check that we still have both black and white regions
    assert np.any(warped == 255)  # White pixels exist
    assert np.any(warped == 0)    # Black pixels exist
    
    # Check that the transformation actually moved the content
    # by comparing the center of mass
    original_center = np.mean(np.where(sample_frame == 255), axis=1)
    warped_center = np.mean(np.where(warped == 255), axis=1)
    assert not np.allclose(original_center, warped_center, atol=5)

def test_apply_corner_pin_edge_cases(sample_frame, sample_corners):
    """Test corner pin transformation with edge cases."""
    # Test with zero-size output
    with pytest.raises(cv2.error):
        apply_corner_pin(sample_frame, sample_corners, (0, 0))
    
    # Test with invalid corners (colinear points)
    invalid_corners = {
        'ul': [0, 0],
        'ur': [100, 0],
        'lr': [200, 0],  # All points on same line
        'll': [300, 0]
    }
    with pytest.raises(cv2.error):
        apply_corner_pin(sample_frame, invalid_corners, (100, 100))
    
    # Test with negative coordinates
    negative_corners = {
        'ul': [-10, -10],
        'ur': [110, -10],
        'lr': [110, 110],
        'll': [-10, 110]
    }
    warped = apply_corner_pin(sample_frame, negative_corners, (100, 100))
    assert warped.shape == (100, 100, 3)

def test_corner_pin_effect_basic(sample_frame, mock_user_clip, mock_corner_pin_data):
    """Test basic corner pin effect functionality."""
    context = {
        "user_clip": mock_user_clip,
        "output_size": (100, 100),
        "corner_pin_data": mock_corner_pin_data,
        "fps": 24,
        "user_offset": 0.0
    }
    
    # Test with mask disabled
    result = corner_pin_effect(sample_frame, t=0.0, use_mask=False, context=context)
    
    # Verify output shape and type
    assert result.shape == sample_frame.shape
    assert result.dtype == np.uint8
    
    # Verify that the effect was applied by checking specific regions
    original_center = sample_frame[45:55, 45:55, :]
    result_center = result[45:55, 45:55, :]
    assert not np.array_equal(original_center, result_center)

def test_corner_pin_effect_time_bounds(sample_frame, mock_user_clip, mock_corner_pin_data):
    """Test corner pin effect at different time points."""
    context = {
        "user_clip": mock_user_clip,
        "output_size": (100, 100),
        "corner_pin_data": mock_corner_pin_data,
        "fps": 24,
        "user_offset": 0.0
    }
    
    # Test before clip duration
    result_before = corner_pin_effect(sample_frame, t=0.0, use_mask=False, context=context)
    
    # Test after clip duration
    result_after = corner_pin_effect(sample_frame, t=2.0, use_mask=False, context=context)
    
    # Results should be different because the clip content changes
    before_center = result_before[45:55, 45:55, :]
    after_center = result_after[45:55, 45:55, :]
    assert not np.array_equal(before_center, after_center)

def test_corner_pin_effect_with_offset(sample_frame, mock_user_clip, mock_corner_pin_data):
    """Test corner pin effect with user offset."""
    context = {
        "user_clip": mock_user_clip,
        "output_size": (100, 100),
        "corner_pin_data": mock_corner_pin_data,
        "fps": 24,
        "user_offset": 0.5
    }
    
    # Test with offset
    result = corner_pin_effect(sample_frame, t=0.0, use_mask=False, context=context)
    
    # Verify output shape and type
    assert result.shape == sample_frame.shape
    assert result.dtype == np.uint8
    
    # Verify that the effect was applied by checking specific regions
    original_center = sample_frame[45:55, 45:55, :]
    result_center = result[45:55, 45:55, :]
    assert not np.array_equal(original_center, result_center)

def test_corner_pin_effect_with_mask_clip(sample_frame, mock_user_clip, mock_corner_pin_data):
    """Test corner pin effect with additional mask clip."""
    # Create a mock mask clip
    class MockMaskClip:
        def __init__(self, duration=1.0):
            self.duration = duration
            
        def get_frame(self, t):
            mask = np.zeros((100, 100), dtype=np.uint8)
            if t < self.duration:
                mask[40:60, 40:60] = 255  # White square in mask
            return mask
    
    context = {
        "user_clip": mock_user_clip,
        "output_size": (100, 100),
        "corner_pin_data": mock_corner_pin_data,
        "fps": 24,
        "user_offset": 0.0,
        "mask_clip": MockMaskClip()
    }
    
    # Test with mask clip
    result = corner_pin_effect(sample_frame, t=0.0, use_mask=True, context=context)
    
    # Verify output shape and type
    assert result.shape == sample_frame.shape
    assert result.dtype == np.uint8
    
    # Verify that the effect was applied by checking specific regions
    original_center = sample_frame[45:55, 45:55, :]
    result_center = result[45:55, 45:55, :]
    assert not np.array_equal(original_center, result_center) 