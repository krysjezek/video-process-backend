from app.tasks.celery_app import celery_app  # Import the pre-configured Celery app
from app.services.scene_processor import process_scene_with_effect_chain
import os
import uuid
import json
import subprocess

# Custom logger class for MoviePy that calls self.update_state() for progress updates
class CeleryProgressLogger:
    def __init__(self, task, scene_id):
        self.task = task
        self.scene_id = scene_id
        self.last_percent = 0

    # MoviePy calls the logger's callback with (current, total, **kwargs)
    def callback(self, current, total, **kwargs):
        if total > 0:
            percent = int((current / total) * 100)
        else:
            percent = 0
        if percent != self.last_percent:
            self.last_percent = percent
            # Update progress for the current scene
            self.task.update_state(state="PROGRESS", meta={"current_scene": self.scene_id, "progress": percent})

@celery_app.task(bind=True)
def process_job(self, mockup_id, scene_order_json, user_video_path):
    # Load configuration for the given mockup
    from app.config import load_mockup_config
    config = load_mockup_config()
    if mockup_id not in config:
        raise ValueError("Invalid mockup identifier.")
    mockup_config = config[mockup_id]
    
    scenes = json.loads(scene_order_json)
    processed_scene_paths = []
    total_scenes = len(scenes)
    
    # Process each scene sequentially
    for index, scene in enumerate(scenes, start=1):
        scene_id = scene["scene_id"]
        scene_timing = {"in_frame": scene["in_frame"], "out_frame": scene["out_frame"]}
        
        scene_config = next((s for s in mockup_config["scenes"] if s["scene_id"] == scene_id), None)
        if scene_config is None:
            raise ValueError(f"Scene {scene_id} not found in mockup.")
        
        scene_output = f"/app/uploads/processed_scenes/{uuid.uuid4()}.mp4"
        
        # Create a custom logger instance for this scene
        logger = CeleryProgressLogger(self, scene_id)
        
        # Process the scene, passing our custom logger to update progress
        process_scene_with_effect_chain(scene_config, user_video_path, scene_timing, scene_output, logger_callback=logger)
        processed_scene_paths.append(scene_output)
        
        # Update overall progress (for example, after each scene, update overall percentage)
        overall_progress = int((index / total_scenes) * 100)
        self.update_state(state="PROGRESS", meta={"overall_progress": overall_progress})
    
    # Concatenate processed scenes using ffmpeg
    final_output = f"/app/uploads/final_outputs/{uuid.uuid4()}.mp4"
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
