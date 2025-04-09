import os
import gc
import json
import numpy as np
import moviepy.editor as mpy
from app.services.effects import EFFECT_REGISTRY
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def apply_effect_chain(t, context, effects_chain):
    """
    Applies each effect in the chain sequentially to the base frame.
    Here, 't' is the local scene time. This function does NOT modify 't' for mockup clips.
    Only the user_clip frame selection inside corner_pin_effect uses the global offset.
    """
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

def assemble_timeline(scene_file_paths, output_path):
    """
    Concatenates processed scene videos into a final composite video.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    clips = [mpy.VideoFileClip(fp) for fp in scene_file_paths]
    final_clip = mpy.concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path, user_video_offset):
    assets = mockup_config.get("assets", {})
    background_path = assets.get("background")
    reflections_path = assets.get("reflections")
    mask_path = assets.get("mask")
    corner_pin_data_path = assets.get("corner_pin_data")
    
    # Load asset clips.
    background_clip = mpy.VideoFileClip(background_path)
    user_clip = mpy.VideoFileClip(user_video_path)
    # Log the user clip duration.
    logger.info("User clip duration: %.3f seconds", user_clip.duration)
    
    reflections_clip = mpy.VideoFileClip(reflections_path)
    mask_clip = mpy.VideoFileClip(mask_path) if mask_path else None

    fps = 24
    # Calculate scene duration from in/out frames.
    scene_duration = (scene_timing["out_frame"] - scene_timing["in_frame"]) / fps

    # Load corner pin tracking data.
    with open(corner_pin_data_path, 'r') as f:
        corner_pin_data = json.load(f)
    
    # Build the context dictionary.
    context = {
        "background_clip": background_clip,
        "user_clip": user_clip,
        "reflections_clip": reflections_clip,
        "mask_clip": mask_clip,
        "corner_pin_data": corner_pin_data,
        "output_size": background_clip.size,  # (width, height)
        "fps": fps,
        "user_offset": user_video_offset
    }
    
    # Use the scene's effects chain or default.
    effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
    
    def make_frame(t):
        from app.services.effects import apply_effect_chain
        return apply_effect_chain(t, context, effects_chain)
    
    full_clip = mpy.VideoClip(make_frame, duration=scene_duration)
    full_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")
    
    # Clean up.
    full_clip.close()
    background_clip.close()
    user_clip.close()
    reflections_clip.close()
    if mask_clip:
        mask_clip.close()
    gc.collect()
