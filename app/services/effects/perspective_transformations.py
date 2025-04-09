import cv2
import numpy as np
import json
import logging

# Set up a logger for this module.
logger = logging.getLogger(__name__)

def apply_corner_pin(frame, corners, output_size):
    """
    Applies a perspective (corner pin) transform to the given frame.
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
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

def corner_pin_effect(frame, t, use_mask, context):
    """
    Applies a corner-pin transformation on the user layer and composites it
    over the current frame. This is the only place where the global user video offset
    (from context["user_offset"]) is applied to select the correct frame from user_clip.
    """
    fps = context["fps"]
    # Calculate global time for the user video.
    global_time = t + context.get("user_offset", 0)
    
    # Log the values so you can see what's happening.
    logger.info("Corner pin effect: t=%.3f, user_offset=%.3f, global_time=%.3f", t, context.get("user_offset", 0), global_time)
    logger.info("User clip duration %.3f", context["user_clip"].duration)
    
    # Select the frame from user_clip based on the global time.
    if global_time < context["user_clip"].duration:
        user_frame = context["user_clip"].get_frame(global_time)
    else:
        h, w = context["output_size"][1], context["output_size"][0]
        user_frame = np.zeros((h, w, 3), dtype=np.uint8)
        logger.info("making black screen")
    
    frame_num = str(int((t * fps) + 1))
    
    if frame_num in context["corner_pin_data"]:
        corners = context["corner_pin_data"][frame_num]
        
        # Scale the corners if needed.
        original_resolution = 3840  # Assuming original resolution.
        current_width = 1920          # Current expected width.
        scale_factor = current_width / original_resolution
        scaled_corners = {
            'ul': [int(corners['ul'][0] * scale_factor), int(corners['ul'][1] * scale_factor)],
            'ur': [int(corners['ur'][0] * scale_factor), int(corners['ur'][1] * scale_factor)],
            'lr': [int(corners['lr'][0] * scale_factor), int(corners['lr'][1] * scale_factor)],
            'll': [int(corners['ll'][0] * scale_factor), int(corners['ll'][1] * scale_factor)]
        }
        
        warped = apply_corner_pin(user_frame, scaled_corners, context["output_size"])
        
        if use_mask:
            h, w = context["output_size"][1], context["output_size"][0]
            corner_mask = np.zeros((h, w), dtype=np.uint8)
            pts = np.array([scaled_corners['ul'], scaled_corners['ur'], scaled_corners['lr'], scaled_corners['ll']], dtype=np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.fillConvexPoly(corner_mask, pts, 255)
            corner_mask_3 = cv2.cvtColor(corner_mask, cv2.COLOR_GRAY2BGR)
            corner_mask_norm = corner_mask_3.astype(np.float32) / 255.0
            
            if "mask_clip" in context and context["mask_clip"] is not None:
                if t < context["mask_clip"].duration:
                    matte_mask_frame = context["mask_clip"].get_frame(t)
                else:
                    matte_mask_frame = np.zeros((h, w), dtype=np.uint8)
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
    else:
        return frame
