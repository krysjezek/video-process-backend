import os
import gc
import json
import moviepy.editor as mpy
from app.services.effects import EFFECT_REGISTRY

def apply_effect_chain(t, context, effects_chain):
    """
    Applies each effect in the chain sequentially to the base frame.
    
    Parameters:
      - t: Current time in seconds.
      - context: Dictionary containing shared assets and parameters.
      - effects_chain: A list of dictionaries specifying each effect and its parameters.
      
    Returns:
      - The resulting composite frame after applying the effects.
    """
    bg_clip = context["background_clip"]
    # If t exceeds the duration of the background clip, loop the background.
    if t > bg_clip.duration:
        t_loop = t % bg_clip.duration
    else:
        t_loop = t
    frame = bg_clip.get_frame(t_loop)
    for effect_item in effects_chain:
        effect_name = effect_item["effect"]
        params = effect_item.get("params", {})
        effect_func = EFFECT_REGISTRY.get(effect_name)
        if effect_func:
            # Notice: we pass the original t here so that effects that use global time (e.g. corner_pin_effect)
            # can apply their own offsets, while the background is looped.
            frame = effect_func(frame, t=t, **params, context=context)
        else:
            raise ValueError(f"Effect '{effect_name}' not found in registry")
    return frame

def assemble_timeline(scene_file_paths, output_path):
    """
    Concatenates processed scene videos into a final composite video.
    
    Parameters:
      - scene_file_paths: List of processed scene video file paths.
      - output_path: The final output path for the composite video.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    clips = [mpy.VideoFileClip(fp) for fp in scene_file_paths]
    final_clip = mpy.concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    
def process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path, user_video_offset):
    """
    Processes a scene using the provided effects chain.
    Adjusts the composite clip so that its duration is governed by the scene timing,
    and ensures that the background loops if it is shorter than the scene.
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

    fps = 24
    scene_duration = (scene_timing["out_frame"] - scene_timing["in_frame"]) / fps

    # Loop the background if its duration is shorter than the desired scene duration.
    if background_clip.duration < scene_duration:
         background_clip = background_clip.loop(duration=scene_duration)
    
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
        "user_offset": user_video_offset  # Global user video time offset
    }
    
    # Use the scene's provided effects chain or fallback to a default.
    effects_chain = mockup_config.get("effects_chain") or mockup_config.get("default_effects_chain", [])
    
    # Define the frame-making function using our updated apply_effect_chain.
    def make_frame(t):
        return apply_effect_chain(t, context, effects_chain)
    
    # Create the full composite clip with duration based on scene timing.
    full_clip = mpy.VideoClip(make_frame, duration=scene_duration)
    full_clip.write_videofile(output_path, fps=context["fps"], codec="libx264", audio_codec="aac")
    
    # Clean up resources.
    full_clip.close()
    background_clip.close()
    user_clip.close()
    reflections_clip.close()
    if mask_clip:
        mask_clip.close()
    gc.collect()
