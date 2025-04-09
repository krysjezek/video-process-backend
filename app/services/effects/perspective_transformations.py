import cv2
import numpy as np
import json
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

def apply_corner_pin(frame, corners, output_size):
    """
    Applies a perspective (corner pin) transform to the given frame.

    Parameters:
      - frame: The user-supplied video frame as a NumPy array.
      - corners: A dictionary containing the destination coordinates with keys:
                 'ul', 'ur', 'lr', 'll'.
      - output_size: Tuple (width, height) for the output frame.
      
    Returns:
      - The warped frame (NumPy array) with the perspective applied.
    """
    h, w = frame.shape[:2]
    src_pts = np.array([[0, 0],
                        [w, 0],
                        [w, h],
                        [0, h]], dtype=np.float32)
    dst_pts = np.array([corners['ul'], corners['ur'], corners['lr'], corners['ll']], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(frame, M, output_size)
    return warped

def load_corner_pin_data(filepath):
    """
    Loads corner pin tracking data from a JSON file.

    Expected JSON structure (keys are frame numbers as strings):
      {
        "0": { "ul": [x, y], "ur": [x, y], "lr": [x, y], "ll": [x, y] },
        "1": { ... },
        ...
      }

    Returns:
      A dictionary mapping frame numbers (as strings) to corner dictionaries.
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

def corner_pin_effect(frame, t, use_mask, context):
    """
    Applies a corner-pin transformation on the user layer and composites it
    over the current frame.

    - The user frame is selected using the global time (local t plus context["user_offset"]).
    - The transformation data (corner pin coordinates) are interpolated using the local scene time t.
    
    Parameters:
      - frame: The current composite frame (e.g., from the background).
      - t: Current time in seconds (local scene time).
      - use_mask: Boolean indicating whether to apply masking.
      - context: Dictionary containing:
          - "user_clip": MoviePy clip for the user video.
          - "corner_pin_data": Dict mapping frame numbers (as strings) to corner coordinates.
          - "output_size": Tuple (width, height) for the output.
          - "fps": Frame rate (e.g., 24).
          - "user_offset": Cumulative offset in seconds for continuous user video playback.
          - "mask_clip": (Optional) The MoviePy clip for a matte mask.
          
    Returns:
      - The updated composite frame (NumPy array) after applying the user layer with perspective transformation.
    """
    fps = context["fps"]
    
    # Calculate global time for selecting the user video frame.
    global_time = t + context.get("user_offset", 0)
    logger.info("Corner pin effect: t=%.3f, user_offset=%.3f, global_time=%.3f", t, context.get("user_offset", 0), global_time)
    
    # Select the user frame using global_time.
    if global_time < context["user_clip"].duration:
        user_frame = context["user_clip"].get_frame(global_time)
    else:
        h_out, w_out = context["output_size"][1], context["output_size"][0]
        user_frame = np.zeros((h_out, w_out, 3), dtype=np.uint8)
    
    # --- Interpolate the corner pin tracking data using local time (t) ---
    # Compute the fractional frame index based on local time.
    frame_index = t * fps
    lower_frame = int(frame_index)
    upper_frame = lower_frame + 1
    fraction = frame_index - lower_frame
    
    tracking_data = context["corner_pin_data"]
    lower_key = str(lower_frame)
    upper_key = str(upper_frame)
    
    if lower_key in tracking_data and upper_key in tracking_data:
        lower_coords = tracking_data[lower_key]
        upper_coords = tracking_data[upper_key]
        interp_coords = {}
        for corner in ['ul', 'ur', 'lr', 'll']:
            interp_coords[corner] = [
                lower_coords[corner][0] * (1 - fraction) + upper_coords[corner][0] * fraction,
                lower_coords[corner][1] * (1 - fraction) + upper_coords[corner][1] * fraction,
            ]
    elif lower_key in tracking_data:
        interp_coords = tracking_data[lower_key]
    else:
        # If no tracking data is available for this frame, return the original frame unmodified.
        return frame
    
    # --- (Optional) Scale the coordinates if needed ---
    original_resolution = 3840  # Assuming the tracking data was captured at 3840 width
    current_width = 1920        # Current expected width of the composite video
    scale_factor = current_width / original_resolution
    scaled_corners = {
        'ul': [int(interp_coords['ul'][0] * scale_factor), int(interp_coords['ul'][1] * scale_factor)],
        'ur': [int(interp_coords['ur'][0] * scale_factor), int(interp_coords['ur'][1] * scale_factor)],
        'lr': [int(interp_coords['lr'][0] * scale_factor), int(interp_coords['lr'][1] * scale_factor)],
        'll': [int(interp_coords['ll'][0] * scale_factor), int(interp_coords['ll'][1] * scale_factor)],
    }
    
    # Apply the perspective transformation using the interpolated and scaled coordinates.
    warped = apply_corner_pin(user_frame, scaled_corners, context["output_size"])
    
    # Optionally apply masking.
    if use_mask:
        h_out, w_out = context["output_size"][1], context["output_size"][0]
        corner_mask = np.zeros((h_out, w_out), dtype=np.uint8)
        pts = np.array([scaled_corners['ul'], scaled_corners['ur'], scaled_corners['lr'], scaled_corners['ll']], dtype=np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.fillConvexPoly(corner_mask, pts, 255)
        corner_mask_3 = cv2.cvtColor(corner_mask, cv2.COLOR_GRAY2BGR)
        corner_mask_norm = corner_mask_3.astype(np.float32) / 255.0
        
        if "mask_clip" in context and context["mask_clip"] is not None:
            if t < context["mask_clip"].duration:
                matte_mask_frame = context["mask_clip"].get_frame(t)
            else:
                matte_mask_frame = np.zeros((h_out, w_out), dtype=np.uint8)
            if matte_mask_frame.ndim == 3 and matte_mask_frame.shape[2] == 3:
                matte_mask_gray = cv2.cvtColor(matte_mask_frame, cv2.COLOR_RGB2GRAY)
            else:
                matte_mask_gray = matte_mask_frame
            matte_mask_norm = matte_mask_gray.astype(np.float32) / 255.0
            matte_mask_3 = cv2.merge([matte_mask_norm, matte_mask_norm, matte_mask_norm])
        else:
            matte_mask_3 = np.ones_like(corner_mask_norm)
        
        final_mask = corner_mask_norm * matte_mask_3
        composite = (warped.astype(np.float32) * final_mask +
                     frame.astype(np.float32) * (1 - final_mask)).astype(np.uint8)
    else:
        user_mask = np.any(warped != 0, axis=2).astype(np.uint8)
        user_mask_3 = cv2.merge([user_mask, user_mask, user_mask]).astype(np.float32)
        composite = (warped.astype(np.float32) * user_mask_3 +
                     frame.astype(np.float32) * (1 - user_mask_3)).astype(np.uint8)
    
    return composite
