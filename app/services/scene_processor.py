import os
import tempfile
import gc
import json
import moviepy.editor as mpy
from app.services.effects import EFFECT_REGISTRY  # Our registry from __init__.py

def apply_effect_chain(t, context, effects_chain):
    """
    Applies each effect in the chain sequentially to the base frame.
    
    Parameters:
      - t: Current time in seconds.
      - context: A dictionary with shared assets and parameters.
      - effects_chain: A list of dictionaries, each with keys "effect" and "params".
    Returns:
      - The resulting frame after all effects are applied.
    """
    # Start with the background frame as the base.
    frame = context["background_clip"].get_frame(t)
    for effect_item in effects_chain:
        effect_name = effect_item["effect"]
        params = effect_item.get("params", {})
        effect_func = EFFECT_REGISTRY.get(effect_name)
        if effect_func:
            frame = effect_func(frame, t=t, **params, context=context)
        else:
            raise ValueError(f"Effect '{effect_name}' not found in registry")
    return frame

def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path, logger_callback=None):
    assets = mockup_config.get("assets", {})
    background_path = assets.get("background")
    reflections_path = assets.get("reflections")
    mask_path = assets.get("mask")
    corner_pin_data_path = assets.get("corner_pin_data")
    
    background_clip = mpy.VideoFileClip(background_path)
    user_clip = mpy.VideoFileClip(user_video_path)
    reflections_clip = mpy.VideoFileClip(reflections_path)
    mask_clip = mpy.VideoFileClip(mask_path) if mask_path else None
    
    with open(corner_pin_data_path, 'r') as f:
        corner_pin_data = json.load(f)
    
    context = {
        "background_clip": background_clip,
        "user_clip": user_clip,
        "reflections_clip": reflections_clip,
        "mask_clip": mask_clip,
        "corner_pin_data": corner_pin_data,
        "output_size": background_clip.size,
        "fps": 24
    }
    
    effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
    
    def make_frame(t):
        return apply_effect_chain(t, context, effects_chain)
    
    full_clip = mpy.VideoClip(make_frame, duration=background_clip.duration)
    start_time = scene_timing["in_frame"] / context["fps"]
    end_time = scene_timing["out_frame"] / context["fps"]
    trimmed_clip = full_clip.subclip(start_time, end_time)
    
    # Pass the logger_callback to write_videofile if provided
    trimmed_clip.write_videofile(output_path, fps=context["fps"], codec="libx264", audio_codec="aac", logger=logger_callback)
    
    full_clip.close()
    trimmed_clip.close()
    background_clip.close()
    user_clip.close()
    reflections_clip.close()
    if mask_clip:
        mask_clip.close()
    
    gc.collect()