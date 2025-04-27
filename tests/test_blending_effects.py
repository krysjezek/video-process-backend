import pytest
import numpy as np
from app.services.effects.blending_effects import screen_blend, reflections_effect

@pytest.fixture
def base_frame():
    """Create a base frame for testing."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[25:75, 25:75, :] = 128  # Gray square in the middle
    return frame

@pytest.fixture
def overlay_frame():
    """Create an overlay frame for testing."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[40:60, 40:60, :] = 128  # Smaller gray square
    return frame

@pytest.fixture
def mock_reflections_clip():
    """Create a mock MoviePy clip for testing reflections."""
    class MockClip:
        def __init__(self, duration=1.0):
            self.duration = duration
            
        def get_frame(self, t):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            if t < self.duration:
                frame[30:70, 30:70, :] = 128  # Gray square
            return frame
    return MockClip()

def test_screen_blend_basic(base_frame, overlay_frame):
    """Test basic screen blend functionality."""
    blended = screen_blend(base_frame, overlay_frame)
    
    # Verify output shape and type
    assert blended.shape == base_frame.shape
    assert blended.dtype == np.uint8
    
    # Verify that blending occurred
    assert not np.array_equal(blended, base_frame)
    assert not np.array_equal(blended, overlay_frame)
    
    # Verify the screen blend formula
    # For gray values, screen blend should be brighter than either input
    base_f = base_frame.astype(np.float32) / 255.0
    overlay_f = overlay_frame.astype(np.float32) / 255.0
    expected = 1 - (1 - base_f) * (1 - overlay_f)
    expected = np.clip(expected * 255, 0, 255).astype(np.uint8)
    assert np.allclose(blended, expected, atol=1)

def test_screen_blend_edge_cases():
    """Test screen blend with edge cases."""
    # Test with all black
    black = np.zeros((10, 10, 3), dtype=np.uint8)
    blended = screen_blend(black, black)
    assert np.array_equal(blended, black)
    
    # Test with all white
    white = np.full((10, 10, 3), 255, dtype=np.uint8)
    blended = screen_blend(white, white)
    assert np.array_equal(blended, white)
    
    # Test with black and white
    blended = screen_blend(black, white)
    assert np.array_equal(blended, white)

def test_reflections_effect_basic(base_frame, mock_reflections_clip):
    """Test basic reflections effect functionality."""
    context = {
        "reflections_clip": mock_reflections_clip,
        "output_size": (100, 100)
    }
    
    # Test with full opacity
    result = reflections_effect(base_frame, t=0.5, opacity=1.0, context=context)
    
    # Verify output shape and type
    assert result.shape == base_frame.shape
    assert result.dtype == np.uint8
    
    # Verify that the effect was applied
    assert not np.array_equal(result, base_frame)
    
    # Test with zero opacity
    result = reflections_effect(base_frame, t=0.5, opacity=0.0, context=context)
    assert np.array_equal(result, base_frame)

def test_reflections_effect_time_bounds(base_frame, mock_reflections_clip):
    """Test reflections effect at different time points."""
    context = {
        "reflections_clip": mock_reflections_clip,
        "output_size": (100, 100)
    }
    
    # Test before clip duration
    result_before = reflections_effect(base_frame, t=0.5, opacity=1.0, context=context)
    
    # Test after clip duration
    result_after = reflections_effect(base_frame, t=2.0, opacity=1.0, context=context)
    
    # Results should be different
    assert not np.array_equal(result_before, result_after)
    
    # After duration should be same as base frame (black overlay)
    assert np.array_equal(result_after, base_frame)

def test_reflections_effect_partial_opacity(base_frame, mock_reflections_clip):
    """Test reflections effect with partial opacity."""
    context = {
        "reflections_clip": mock_reflections_clip,
        "output_size": (100, 100)
    }
    
    # Test with 50% opacity
    result = reflections_effect(base_frame, t=0.5, opacity=0.5, context=context)
    
    # Result should be between base frame and full blend
    full_blend = reflections_effect(base_frame, t=0.5, opacity=1.0, context=context)
    
    # Calculate differences
    diff_base = np.abs(result.astype(float) - base_frame.astype(float))
    diff_blend = np.abs(result.astype(float) - full_blend.astype(float))
    
    # Result should be closer to base frame than to full blend
    assert np.mean(diff_base) < np.mean(diff_blend) 