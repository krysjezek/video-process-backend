# app/tasks/processing_tasks.py
from celery import Celery
from app.services.scene_processor import process_scene_with_effect_chain
from app.services.timeline_assembler import assemble_timeline
import os
import uuid
import json

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def process_job(mockup_id, scene_order_json, user_video_path):
    # Load configuration for the given mockup (same as above)
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
        
        scene_output = f"uploads/processed_scenes/{uuid.uuid4()}.mp4"
        process_scene_with_effect_chain(scene_config, user_video_path, scene_timing, scene_output)
        processed_scene_paths.append(scene_output)
    
    final_output = f"uploads/final_outputs/{uuid.uuid4()}.mp4"
    assemble_timeline(processed_scene_paths, final_output)
    
    return final_output
