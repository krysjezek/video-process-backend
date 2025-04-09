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

def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path, user_video_offset):
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

    # Calculate the intended scene duration in seconds using scene timing.
    fps = 24
    scene_duration = (scene_timing["out_frame"] - scene_timing["in_frame"]) / fps

    # If the background asset is shorter than the scene duration, loop it.
    if background_clip.duration < scene_duration:
         background_clip = background_clip.loop(duration=scene_duration)
    
    # Load corner pin tracking data.
    with open(corner_pin_data_path, 'r') as f:
        corner_pin_data = json.load(f)
    
    # Build a context dictionary for the effect functions.
    context = {
        "background_clip": background_clip,
        "user_clip": user_clip,
        "reflections_clip": reflections_clip,
        "mask_clip": mask_clip,
        "corner_pin_data": corner_pin_data,
        "output_size": background_clip.size,  # (width, height)
        "fps": fps,
        "user_offset": user_video_offset  # Pass along the cumulative user video offset.
    }
    
    # Use scene-specific effects chain if provided; otherwise fallback to default.
    effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
    
    # Define a frame function that applies the effect chain.
    def make_frame(t):
        # 't' here is relative to the scene (0 to scene_duration)
        return apply_effect_chain(t, context, effects_chain)
    
    # **** Updated: Use scene_duration to set the composite clip duration ****
    full_clip = mpy.VideoClip(make_frame, duration=scene_duration)
    
    # Since full_clip now has the duration specified by scene_timing,
    # we do not need to subclip it.
    full_clip.write_videofile(output_path, fps=context["fps"], codec="libx264", audio_codec="aac")
    
    # Clean up: Close all clips to free memory.
    full_clip.close()
    background_clip.close()
    user_clip.close()
    reflections_clip.close()
    if mask_clip:
        mask_clip.close()
    
    # Force garbage collection.
    gc.collect()


