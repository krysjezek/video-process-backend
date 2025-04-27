# app/services/effects/blur_effect.py

import cv2
import numpy as np
from typing import Optional, Dict, Any

def gauss_blur_effect(
    frame: np.ndarray,
    t: float,
    context: Dict[str, Any],
    sigma: float = 1.0,
    roi_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Apply Gaussian blur to the input frame.
    
    Parameters:
        frame (np.ndarray): Input frame (H x W x 3)
        t (float): Current time in seconds (unused)
        context (Dict[str, Any]): Additional context (unused)
        sigma (float): Standard deviation of the Gaussian kernel
        roi_mask (Optional[np.ndarray]): Binary mask (H x W) where 1 indicates regions to blur
        
    Returns:
        np.ndarray: Blurred frame
    """
    # Calculate kernel size from sigma (OpenCV requires odd kernel size)
    ksize = int(6 * sigma + 1)
    ksize = ksize + 1 if ksize % 2 == 0 else ksize
    
    # Apply blur to each channel
    blurred = np.zeros_like(frame)
    for i in range(3):
        blurred[..., i] = cv2.GaussianBlur(
            frame[..., i],
            (ksize, ksize),
            sigmaX=sigma,
            sigmaY=sigma
        )
    
    # If ROI mask is provided, blend original and blurred frames
    if roi_mask is not None:
        # Ensure mask is 3D for broadcasting
        mask_3d = roi_mask[..., np.newaxis]
        blurred = frame * (1 - mask_3d) + blurred * mask_3d
    
    return blurred
