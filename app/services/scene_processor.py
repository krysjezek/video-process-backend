import os
import gc
import json
import numpy as np
import moviepy.editor as mpy
from app.services.effects import EFFECT_REGISTRY
from app.config.logging import get_logger

logger = get_logger(component="scene_processor")

def apply_effect_chain(t, context, effects_chain):
    """
    Applies each effect in the chain sequentially to the base frame.
    Here, 't' is the local scene time. This function does NOT modify 't' for mockup clips.
    Only the user_clip frame selection inside corner_pin_effect uses the global offset.
    """
    try:
        bg_clip = context["background_clip"]
        if t < bg_clip.duration:
            frame = bg_clip.get_frame(t)
        else:
            h, w = context["output_size"][1], context["output_size"][0]
            frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        for effect_item in effects_chain:
            effect_name = effect_item["effect"]
            params = effect_item.get("params", {})
            effect_func = EFFECT_REGISTRY.get(effect_name)
            if effect_func:
                # Pass t as-is to all effects; the corner_pin_effect will adjust for the user video.
                frame = effect_func(frame, t=t, **params, context=context)
            else:
                raise ValueError(f"Effect '{effect_name}' not found in registry")
        return frame
    except Exception as e:
        logger.error("Error in apply_effect_chain", error=str(e), exc_info=True)
        raise

def assemble_timeline(scene_file_paths, output_path):
    """
    Concatenates processed scene videos into a final composite video.
    """
    try:
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        clips = [mpy.VideoFileClip(fp) for fp in scene_file_paths]
        final_clip = mpy.concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    except Exception as e:
        logger.error("Error in assemble_timeline", error=str(e), exc_info=True)
        raise

def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path, user_video_offset):
    """
    Processes a single scene using the defined effects chain.
    The scene's duration is based on its timing (in/out frames), and only the user_clip
    frame selection (in corner_pin_effect) is adjusted with the global offset.
    """
    try:
        assets = mockup_config.get("assets", {})
        background_path = assets.get("background")
        reflections_path = assets.get("reflections")
        mask_path = assets.get("mask")
        corner_pin_data_path = assets.get("corner_pin_data")
        
        # Load asset clips.
        background_clip = mpy.VideoFileClip(background_path)
        user_clip = mpy.VideoFileClip(user_video_path)
        reflections_clip = mpy.VideoFileClip(reflections_path)
        mask_clip = mpy.VideoFileClip(mask_path) if mask_path else None

        fps = 24
        # Calculate scene duration from the provided in/out frame numbers.
        scene_duration = (scene_timing["out_frame"] - scene_timing["in_frame"]) / fps

        # Load corner pin tracking data.
        with open(corner_pin_data_path, 'r') as f:
            corner_pin_data = json.load(f)
        
        # Build the context dictionary. Note: 'user_offset' is used only when selecting from user_clip.
        context = {
            "background_clip": background_clip,
            "user_clip": user_clip,
            "reflections_clip": reflections_clip,
            "mask_clip": mask_clip,
            "corner_pin_data": corner_pin_data,
            "output_size": background_clip.size,  # Use original video size
            "fps": fps,
            "user_offset": user_video_offset
        }
        
        # Choose the scene's effects chain, falling back to default if necessary.
        effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
        
        # Define the frame-making function using the local scene time.
        def make_frame(t):
            return apply_effect_chain(t, context, effects_chain)
        
        # Create the composite clip for the scene with the duration derived from scene_timing.
        full_clip = mpy.VideoClip(make_frame, duration=scene_duration)
        full_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")
        
        # Clean up to free memory.
        full_clip.close()
        background_clip.close()
        user_clip.close()
        reflections_clip.close()
        if mask_clip:
            mask_clip.close()
        gc.collect()
    except Exception as e:
        logger.error("Error in process_scene_with_effect_chain", error=str(e), exc_info=True)
        raise
