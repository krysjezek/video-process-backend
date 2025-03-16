# app/services/effects/corner_pin.py
import cv2
import numpy as np
import json

def apply_corner_pin(frame, corners, output_size):
    """
    Applies a perspective (corner pin) transform to the given frame.

    Parameters:
      - frame: The user-supplied video frame as a NumPy array.
      - corners: A dictionary containing the destination coordinates with keys:
                 'ul', 'ur', 'lr', 'll' (ordered as top-left, top-right, bottom-right, bottom-left).
                 Each value should be a list or tuple of [x, y].
      - output_size: Tuple (width, height) for the size of the output frame.

    Returns:
      - The warped frame (NumPy array) with the perspective applied.
    """
    h, w = frame.shape[:2]
    
    # Define source points as the corners of the full input frame
    src_pts = np.array([[0, 0],
                        [w, 0],
                        [w, h],
                        [0, h]], dtype=np.float32)
    
    # Define destination points from the tracking data.
    dst_pts = np.array([corners['ul'], corners['ur'], corners['lr'], corners['ll']], dtype=np.float32)
    
    # Compute the perspective transform matrix.
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # Warp the frame into the output size.
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
    Applies a corner-pin transformation on the user layer and composites it over the current frame.
    
    If `use_mask` is True and a matte mask is provided (via context["mask_clip"]),
    this function uses both a polygon mask (derived from the corner pin data)
    and the matte mask (from mask.mov) to refine the region where the user layer is applied.
    
    Parameters:
      - frame: The current composite frame (typically from the background).
      - t: Current time in seconds.
      - use_mask: Boolean indicating whether to apply masking.
      - context: Dictionary containing shared assets and parameters:
            - "user_clip": The MoviePy clip for the user video.
            - "mask_clip": The MoviePy clip for the matte mask (if available).
            - "corner_pin_data": Dict mapping frame numbers (as strings) to corner coordinates.
            - "output_size": Tuple (width, height) for the output.
            - "fps": Frame rate (e.g., 24).
    Returns:
      - The updated composite frame (NumPy array) after applying the user layer with masking.
    """
    fps = context["fps"]
    frame_num = str(int(t * fps))
    
    if frame_num in context["corner_pin_data"]:
        corners = context["corner_pin_data"][frame_num]
        
        # Retrieve the user frame (or a black frame if the user clip has ended)
        if t < context["user_clip"].duration:
            user_frame = context["user_clip"].get_frame(t)
        else:
            h, w = context["output_size"][1], context["output_size"][0]
            user_frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Apply the corner pin transformation
        warped = apply_corner_pin(user_frame, corners, context["output_size"])
        
        if use_mask:
            h, w = context["output_size"][1], context["output_size"][0]
            
            # Create a polygon mask from the destination corners.
            corner_mask = np.zeros((h, w), dtype=np.uint8)
            pts = np.array([corners['ul'], corners['ur'], corners['lr'], corners['ll']], dtype=np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.fillConvexPoly(corner_mask, pts, 255)
            corner_mask_3 = cv2.cvtColor(corner_mask, cv2.COLOR_GRAY2BGR)
            corner_mask_norm = corner_mask_3.astype(np.float32) / 255.0
            
            # --- Retrieve the additional matte mask from mask_clip ---
            if "mask_clip" in context and context["mask_clip"] is not None:
                if t < context["mask_clip"].duration:
                    matte_mask_frame = context["mask_clip"].get_frame(t)
                else:
                    matte_mask_frame = np.zeros((h, w), dtype=np.uint8)
                
                # If the matte mask frame has 3 channels, convert it to grayscale.
                if matte_mask_frame.ndim == 3 and matte_mask_frame.shape[2] == 3:
                    matte_mask_gray = cv2.cvtColor(matte_mask_frame, cv2.COLOR_RGB2GRAY)
                else:
                    matte_mask_gray = matte_mask_frame
                
                matte_mask_norm = matte_mask_gray.astype(np.float32) / 255.0
                # Convert the single-channel matte mask to 3 channels.
                matte_mask_3 = cv2.merge([matte_mask_norm, matte_mask_norm, matte_mask_norm])
            else:
                # If no matte mask is provided, use a full white mask.
                matte_mask_3 = np.ones_like(corner_mask_norm)
            
            # --- Combine the polygon mask with the matte mask ---
            final_mask = corner_mask_norm * matte_mask_3
            
            # Composite the warped (user) frame onto the current base frame using the final mask.
            composite = (warped.astype(np.float32) * final_mask +
                         frame.astype(np.float32) * (1 - final_mask)).astype(np.uint8)
        else:
            composite = warped
        
        return composite
    else:
        # If no corner pin data is available for this frame, return the original frame.
        return frame