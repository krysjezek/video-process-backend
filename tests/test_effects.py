import pytest
import numpy as np
from app.services.effects.blur_effect import gauss_blur_effect

@pytest.fixture
def sample_frame():
    """Create a sample frame for testing."""
    # Create a 100x100 RGB frame with a checkerboard pattern
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        for j in range(100):
            if (i // 10 + j // 10) % 2 == 0:
                frame[i, j, 0] = 255  # Red channel checkerboard
                frame[i, j, 1] = 255  # Green channel checkerboard
    return frame

@pytest.fixture
def sample_mask():
    """Create a sample ROI mask for testing."""
    # Create a binary mask with a circle in the center
    mask = np.zeros((100, 100), dtype=np.uint8)
    center = (50, 50)
    radius = 30
    for y in range(100):
        for x in range(100):
            if (x - center[0])**2 + (y - center[1])**2 <= radius**2:
                mask[y, x] = 1
    return mask

def test_gauss_blur_basic(sample_frame):
    """Test basic Gaussian blur functionality."""
    # Apply blur with default sigma
    blurred = gauss_blur_effect(sample_frame, t=0.0, context={})
    
    # Verify output shape and type
    assert blurred.shape == sample_frame.shape
    assert blurred.dtype == np.uint8
    
    # Verify that blurring actually occurred
    # The blurred image should be different from the original
    assert not np.array_equal(blurred, sample_frame)
    
    # Verify that the blur is symmetric by checking a small region
    # Compare a 3x3 patch in the center of the image
    center = 50
    patch_size = 3
    patch_x = blurred[center-patch_size:center+patch_size, center, 0]
    patch_y = blurred[center, center-patch_size:center+patch_size, 0]
    assert np.allclose(patch_x, patch_y, rtol=0.1)

def test_gauss_blur_with_roi(sample_frame, sample_mask):
    """Test Gaussian blur with ROI mask."""
    # Apply blur with ROI mask and increased sigma for more noticeable effect
    blurred = gauss_blur_effect(sample_frame, t=0.0, context={}, roi_mask=sample_mask, sigma=5.0)
    
    # Verify output shape and type
    assert blurred.shape == sample_frame.shape
    assert blurred.dtype == np.uint8
    
    # Verify that areas outside the mask are unchanged
    outside_mask = np.where(sample_mask == 0)
    assert np.array_equal(blurred[outside_mask], sample_frame[outside_mask])
    
    # Verify that areas inside the mask are blurred
    # Compare the mean absolute difference between original and blurred
    inside_mask = np.where(sample_mask == 1)
    diff = np.abs(blurred[inside_mask].astype(float) - sample_frame[inside_mask].astype(float))
    assert np.mean(diff) > 0.1  # Expect some difference due to blur

def test_gauss_blur_different_sigmas(sample_frame):
    """Test Gaussian blur with different sigma values."""
    # Test with small sigma
    blurred_small = gauss_blur_effect(sample_frame, t=0.0, context={}, sigma=0.5)
    
    # Test with large sigma
    blurred_large = gauss_blur_effect(sample_frame, t=0.0, context={}, sigma=2.0)
    
    # Verify that larger sigma produces more blur
    # Calculate the difference between original and blurred
    diff_small = np.abs(blurred_small.astype(float) - sample_frame.astype(float))
    diff_large = np.abs(blurred_large.astype(float) - sample_frame.astype(float))
    
    # The larger sigma should produce larger differences
    assert np.mean(diff_large) > np.mean(diff_small)

def test_gauss_blur_edge_cases(sample_frame):
    """Test edge cases for Gaussian blur."""
    # Test with sigma = 0 (should be equivalent to no blur)
    blurred_zero = gauss_blur_effect(sample_frame, t=0.0, context={}, sigma=0.0)
    assert np.array_equal(blurred_zero, sample_frame)
    
    # Test with very large sigma
    blurred_large = gauss_blur_effect(sample_frame, t=0.0, context={}, sigma=10.0)
    # Verify the output is still valid
    assert blurred_large.shape == sample_frame.shape
    assert blurred_large.dtype == np.uint8
    assert np.all(blurred_large >= 0) and np.all(blurred_large <= 255) 