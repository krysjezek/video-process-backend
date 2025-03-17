from app.tasks.celery_app import celery_app  # Import the pre-configured Celery app
from app.services.scene_processor import process_scene_with_effect_chain
from app.services.timeline_assembler import assemble_timeline
import os
import uuid
import json
import subprocess

@celery_app.task
def process_job(mockup_id, scene_order_json, user_video_path):
    # Load configuration for the given mockup
    from app.config import load_mockup_config
    config = load_mockup_config()
    if mockup_id not in config:
        raise ValueError("Invalid mockup identifier.")
    mockup_config = config[mockup_id]
    
    scenes = json.loads(scene_order_json)
    processed_scene_paths = []
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        scene_timing = {"in_frame": scene["in_frame"], "out_frame": scene["out_frame"]}
        
        scene_config = next((s for s in mockup_config["scenes"] if s["scene_id"] == scene_id), None)
        if scene_config is None:
            raise ValueError(f"Scene {scene_id} not found in mockup.")
        
        scene_output = f"/app/uploads/processed_scenes/{uuid.uuid4()}.mp4"
        process_scene_with_effect_chain(scene_config, user_video_path, scene_timing, scene_output)
        processed_scene_paths.append(scene_output)
    
    final_output = f"/app/uploads/final_outputs/{uuid.uuid4()}.mp4"
    # Concatenate scenes with ffmpeg
    concat_list = "/app/uploads/concat_list.txt"
    with open(concat_list, "w") as f:
        for scene_path in processed_scene_paths:
            f.write(f"file '{scene_path}'\n")
    
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-c:a", "aac", "-y", final_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg concatenation failed: {result.stderr}")
        raise Exception("Failed to concatenate scenes with FFmpeg")
    
    if os.path.exists(concat_list):
        os.remove(concat_list)
    
    return final_output
