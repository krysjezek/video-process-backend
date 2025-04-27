from celery import Celery
from app.config.logging import get_logger, init_logging
from app.config.exceptions import VideoProcessingError
from app.services.scene_processor import process_scene_with_effect_chain
from app.services.timeline_assembler import assemble_timeline
from app.services.storage import storage
import os
import uuid
import json
import subprocess
import gc
import psutil
from typing import Any, Dict, List
from app.tasks.celery_app import celery_app  # Import the pre-configured Celery app

# Get logger
logger = get_logger(component="worker")

def log_memory_usage():
    """Log current memory usage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    logger.info(
        "memory_usage",
        rss_mb=mem_info.rss / 1024 / 1024,
        vms_mb=mem_info.vms / 1024 / 1024
    )

# Initialize Celery app
celery_app = Celery('tasks')
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable='UTC',
)

def parse_scenes(video_path: str) -> List[Dict[str, Any]]:
    """Parse the video path string into a list of scene configurations."""
    try:
        scenes = json.loads(video_path)
        if not isinstance(scenes, list):
            raise ValueError("Expected a list of scenes")
        for scene in scenes:
            if not isinstance(scene, dict) or "scene_id" not in scene:
                raise ValueError("Invalid scene format")
        return scenes
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")

@celery_app.task(bind=True, name='process_video')
def process_video(self, mockup_id: str, scene_order_json: str, video_key: str) -> Dict[str, Any]:
    """Process a video with the given mockup and scene order."""
    job_id = self.request.id
    task_logger = logger.bind(job_id=job_id, mockup_id=mockup_id)

    try:
        task_logger.info(
            "starting_video_processing",
            scene_order=scene_order_json,
            video_key=video_key
        )
        log_memory_usage()

        # Download the input video from MinIO
        temp_video_path = f"/tmp/{uuid.uuid4()}.mp4"
        try:
            storage.get_object(video_key, temp_video_path)
        except Exception as e:
            task_logger.error("failed_to_download_video", error=str(e))
            raise VideoProcessingError(f"Failed to download video: {str(e)}")

        try:
            # Load mockup configuration
            from app.config import load_mockup_config
            config = load_mockup_config()
            if mockup_id not in config:
                raise ValueError(f"Invalid mockup identifier: {mockup_id}")
            mockup_config = config[mockup_id]

            # Parse scene order
            scenes = json.loads(scene_order_json)
            processed_scene_paths = []
            user_video_offset = 0.0
            fps = 24

            # Process each scene
            for index, scene in enumerate(scenes, start=1):
                scene_id = scene["scene_id"]
                scene_timing = {
                    "in_frame": scene["in_frame"],
                    "out_frame": scene["out_frame"]
                }

                # Get scene config
                scene_config = next(
                    (s for s in mockup_config["scenes"] if s["scene_id"] == scene_id),
                    None
                )
                if not scene_config:
                    raise ValueError(f"Scene {scene_id} not found in mockup configuration")

                # Process scene
                scene_output = f"/tmp/{job_id}_scene_{index}.mp4"
                process_scene_with_effect_chain(
                    mockup_config=scene_config,
                    user_video_path=temp_video_path,
                    scene_timing=scene_timing,
                    output_path=scene_output,
                    user_video_offset=user_video_offset
                )
                processed_scene_paths.append(scene_output)
                user_video_offset += (scene_timing["out_frame"] - scene_timing["in_frame"]) / fps

                # Clean up after each scene
                gc.collect()
                log_memory_usage()

            # Assemble final timeline
            final_output = f"/tmp/{job_id}_final.mp4"
            assemble_timeline(processed_scene_paths, final_output)

            # Upload final video to MinIO
            final_key = f"outputs/{job_id}.mp4"
            storage.put_object(final_key, final_output)

            task_logger.info("video_processing_completed")
            log_memory_usage()

            return {
                "status": "success",
                "job_id": job_id,
                "output_path": final_key
            }

        finally:
            # Clean up temporary files
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            for scene_path in processed_scene_paths:
                if os.path.exists(scene_path):
                    os.remove(scene_path)
            if os.path.exists(final_output):
                os.remove(final_output)

    except ValueError as e:
        task_logger.error("video_processing_failed_value_error", error=str(e))
        raise VideoProcessingError(f"Configuration or Input Error: {str(e)}")

    except Exception as e:
        task_logger.error("video_processing_failed_unexpected", error=str(e))
        raise VideoProcessingError(f"Failed to process video: {str(e)}") 
