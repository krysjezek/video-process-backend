import cv2
import numpy as np

def screen_blend(base, overlay):
    """
    Applies a screen blend effect between two frames.
    
    For each pixel: result = 1 - (1 - base) * (1 - overlay)
    Assumes input frames are in the 0-255 range.
    """
    base_f = base.astype(np.float32) / 255.0
    overlay_f = overlay.astype(np.float32) / 255.0
    blended = 1 - (1 - base_f) * (1 - overlay_f)
    return np.clip(blended * 255, 0, 255).astype(np.uint8)

def reflections_effect(frame, t, opacity, context):
    """
    Blends the reflections clip over the current frame using a screen blend.
    
    Parameters:
      - frame: The current composite frame.
      - t: Current time in seconds.
      - opacity: A float (e.g., 0.5) for blending opacity.
      - context: Dictionary containing:
            - "reflections_clip": MoviePy clip for reflections.
            - "output_size": (width, height) tuple.
            
    Returns:
      - The updated composite frame with reflections blended.
    """
    if t < context["reflections_clip"].duration:
        refl_frame = context["reflections_clip"].get_frame(t)
    else:
        h, w = context["output_size"][1], context["output_size"][0]
        refl_frame = np.zeros((h, w, 3), dtype=np.uint8)
    blended = screen_blend(frame, refl_frame)
    # Apply alpha blending: combine original frame and blended result.
    return (frame.astype(np.float32) * (1 - opacity) +
            blended.astype(np.float32) * opacity).astype(np.uint8)
