import os
import tempfile
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

def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path):
    """
    Processes a single scene using the effects chain defined in the mockup configuration.
    
    Parameters:
      - mockup_config: Dictionary containing the mockup’s assets and effects chain.
          Example:
            {
              "assets": {
                  "background": "assets/mockup1/background.mp4",
                  "reflections": "assets/mockup1/reflections.mp4",
                  "mask": "assets/mockup1/mask.mov",
                  "corner_pin_data": "assets/mockup1/corner_pin_data.json"
              },
              "effects_chain": [
                  {"effect": "corner_pin", "params": {"use_mask": true}},
                  {"effect": "reflections", "params": {"opacity": 0.5}}
              ]
            }
      - user_video_path: Path to the user’s source video.
      - scene_timing: Dictionary with "in_frame" and "out_frame" (integers, at 24 fps) for trimming.
      - output_path: Where to save the processed scene video.
    """
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
        "fps": 24
    }
    
    effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
    
    # Define a frame function that applies the effect chain.
    def make_frame(t):
        return apply_effect_chain(t, context, effects_chain)
    
    # Create a full composite clip for the scene.
    full_clip = mpy.VideoClip(make_frame, duration=background_clip.duration)
    
    # Trim the clip according to scene timing (convert frame numbers to seconds).
    start_time = scene_timing["in_frame"] / context["fps"]
    end_time = scene_timing["out_frame"] / context["fps"]
    trimmed_clip = full_clip.subclip(start_time, end_time)
    
    # Write the processed scene video.
    trimmed_clip.write_videofile(output_path, fps=context["fps"], codec="libx264", audio_codec="aac")
