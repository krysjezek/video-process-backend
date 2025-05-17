import cv2
import numpy as np
from typing import Dict, Any
from .blur_effect import gauss_blur_effect
from .blending_effects import screen_blend

def screen_glow_effect(
    frame: np.ndarray,
    t: float,
    context: Dict[str, Any],
    blur_sigma: float = 2.0,
    glow_opacity: float = 0.5
) -> np.ndarray:
    """
    Creates a screen glow effect by blurring the input frame and blending it with the original.
    
    Parameters:
        frame (np.ndarray): Input frame (H x W x 3)
        t (float): Current time in seconds (unused)
        context (Dict[str, Any]): Additional context
        blur_sigma (float): Standard deviation for Gaussian blur
        glow_opacity (float): Opacity of the glow effect (0.0 to 1.0)
        
    Returns:
        np.ndarray: Frame with glow effect applied
    """
    # Create a blurred version of the frame
    blurred = gauss_blur_effect(frame, t, context, sigma=blur_sigma)
    
    # Screen blend the blurred version with the original
    # This creates the glow effect
    glow = screen_blend(frame, blurred)
    
    # Blend the glow with the original frame based on opacity
    result = (frame.astype(np.float32) * (1 - glow_opacity) +
             glow.astype(np.float32) * glow_opacity).astype(np.uint8)
    
    return result 