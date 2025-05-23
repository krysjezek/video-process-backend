import cv2
import numpy as np
import json
from app.config.logging import get_logger
from .blur_effect import gauss_blur_effect

# Set up a logger for this module.
logger = get_logger(component="perspective_transformations")

def apply_corner_pin(frame, corners, output_size):
    """
    Applies a perspective (corner pin) transform to the given frame.
    
    Args:
        frame: Input frame to transform
        corners: Dictionary containing corner points (ul, ur, lr, ll)
        output_size: Tuple of (width, height) for output frame
        
    Returns:
        Transformed frame
        
    Raises:
        cv2.error: If the transformation cannot be computed
    """
    if output_size[0] <= 0 or output_size[1] <= 0:
        logger.error("Invalid output size", output_size=output_size)
        raise cv2.error("Invalid output size")
        
    h, w = frame.shape[:2]
    logger.debug("Input frame dimensions", height=h, width=w)
    
    # Source points (original frame corners)
    src_pts = np.array([[0, 0],
                        [w, 0],
                        [w, h],
                        [0, h]], dtype=np.float32)
    
    # Destination points (corner pin points)
    dst_pts = np.array([corners['ul'], corners['ur'], corners['lr'], corners['ll']], dtype=np.float32)
    
    # Calculate perspective transform
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # Apply the transformation with better interpolation
    warped = cv2.warpPerspective(frame, M, output_size)
    
    return warped

def load_corner_pin_data(filepath):
    """
    Loads corner pin tracking data from a JSON file.
    """
    logger.debug("loading_corner_pin_data", filepath=filepath)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.debug("corner_pin_data_loaded", frame_count=len(data))
        return data
    except (IOError, json.JSONDecodeError) as e:
        logger.error("Failed to load corner pin data", filepath=filepath, error=str(e))
        raise

def corner_pin_effect(frame, t, use_mask, context, blur_enabled=False, blur_sigma=1.5, blur_opacity=0.3):
    """
    Applies a corner-pin transformation on the user layer and composites it
    over the current frame. This is the only place where the global user video offset
    (from context["user_offset"]) is applied to select the correct frame from user_clip.
    
    Args:
        frame: Current frame
        t: Current time
        use_mask: Whether to use the mask clip
        context: Context dictionary containing clips and data
        blur_enabled: Whether to apply blur effect
        blur_sigma: Sigma value for Gaussian blur
        blur_opacity: Opacity of the blurred version (0.0 to 1.0)
    """
    try:
        fps = context["fps"]
        # Calculate global time for the user video.
        global_time = t + context.get("user_offset", 0)
        
        # Log the values for debugging
        logger.debug("Corner pin effect: t=%.3f, user_offset=%.3f, global_time=%.3f", 
                    t, context.get("user_offset", 0), global_time)
        logger.debug("User clip duration %.3f", context["user_clip"].duration)
        
        # Select the frame from user_clip based on the global time.
        if global_time < context["user_clip"].duration:
            user_frame = context["user_clip"].get_frame(global_time)
        else:
            h, w = context["output_size"][1], context["output_size"][0]
            user_frame = np.zeros((h, w, 3), dtype=np.uint8)
            logger.debug("Using black frame (past user clip duration)")
        
        frame_num = str(round(t * fps))
        
        if frame_num in context["corner_pin_data"]:
            corners = context["corner_pin_data"][frame_num]
            
            # Scale the corners using the old version's approach
            original_resolution = 3840  # Source width from After Effects
            current_width = 1920        # Target width
            scale_factor = current_width / original_resolution  # Back to original scaling
            
            # Scale both X and Y coordinates with the same factor to maintain aspect ratio
            scaled_corners = {
                'ul': [int(corners['ul'][0] * scale_factor), int(corners['ul'][1] * scale_factor)],
                'ur': [int(corners['ur'][0] * scale_factor), int(corners['ur'][1] * scale_factor)],
                'lr': [int(corners['lr'][0] * scale_factor), int(corners['lr'][1] * scale_factor)],
                'll': [int(corners['ll'][0] * scale_factor), int(corners['ll'][1] * scale_factor)]
            }
            
            logger.debug(
                "Corner pin scaling",
                original_corners=corners,
                scaled_corners=scaled_corners,
                scale_factor=scale_factor,
                original_resolution=original_resolution,
                current_width=current_width
            )
            
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
                
                # First apply the mask to get the masked content
                masked_content = (warped.astype(np.float32) * final_mask).astype(np.uint8)
                
                if blur_enabled:
                    # Create a blurred version of the masked content
                    blurred_content = gauss_blur_effect(masked_content, t, context, sigma=blur_sigma)
                    
                    # Create a glow layer by blending the blurred content with the original
                    glow_layer = cv2.addWeighted(masked_content, 1 - blur_opacity, blurred_content, blur_opacity, 0)
                    
                    # Composite the glow layer behind the original content
                    # First, composite the glow onto the background
                    composite = (glow_layer.astype(np.float32) +
                                frame.astype(np.float32) * (1 - final_mask)).astype(np.uint8)
                    
                    # Then, composite the original sharp content on top
                    composite = (masked_content.astype(np.float32) * final_mask +
                                composite.astype(np.float32) * (1 - final_mask)).astype(np.uint8)
                else:
                    # Just composite the original content
                    composite = (masked_content.astype(np.float32) +
                                frame.astype(np.float32) * (1 - final_mask)).astype(np.uint8)
            else:
                user_mask = np.any(warped != 0, axis=2).astype(np.uint8)
                user_mask_3 = cv2.merge([user_mask, user_mask, user_mask]).astype(np.float32)
                
                # First apply the mask to get the masked content
                masked_content = (warped.astype(np.float32) * user_mask_3).astype(np.uint8)
                
                if blur_enabled:
                    # Create a blurred version of the masked content
                    blurred_content = gauss_blur_effect(masked_content, t, context, sigma=blur_sigma)
                    
                    # Create a glow layer by blending the blurred content with the original
                    glow_layer = cv2.addWeighted(masked_content, 1 - blur_opacity, blurred_content, blur_opacity, 0)
                    
                    # Composite the glow layer behind the original content
                    # First, composite the glow onto the background
                    composite = (glow_layer.astype(np.float32) +
                                frame.astype(np.float32) * (1 - user_mask_3)).astype(np.uint8)
                    
                    # Then, composite the original sharp content on top
                    composite = (masked_content.astype(np.float32) * user_mask_3 +
                                composite.astype(np.float32) * (1 - user_mask_3)).astype(np.uint8)
                else:
                    # Just composite the original content
                    composite = (masked_content.astype(np.float32) +
                                frame.astype(np.float32) * (1 - user_mask_3)).astype(np.uint8)
            
            return composite
        else:
            logger.warning("No corner pin data found for frame", frame_number=frame_num)
            return frame
    except Exception as e:
        logger.error("Error in corner_pin_effect", error=str(e), exc_info=True)
        raise
