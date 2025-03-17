import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from app.tasks.processing_tasks import process_job
from app.config import load_mockup_config  # A helper function to load your mockups configuration

router = APIRouter()

@router.post("/submit-job")
async def submit_job(
    mockup_id: str = Form(...),
    scene_order: str = Form(...),  # Expected to be a JSON string
    file: UploadFile = File(...)
):
    """
    Endpoint to submit a video processing job.
    
    Expects:
      - mockup_id: Identifier for the desired mockup.
      - scene_order: JSON string specifying the scene order and timings.
      - file: The user's source video file.
    
    Returns:
      A JSON response containing the job ID.
    """
    # Save the uploaded user video.
    user_video_dir = "uploads/user_videos"
    os.makedirs(user_video_dir, exist_ok=True)
    user_video_path = os.path.join(user_video_dir, f"{uuid.uuid4()}.mp4")
    try:
        with open(user_video_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Load mockup configuration.
    config = load_mockup_config()
    if mockup_id not in config:
        raise HTTPException(status_code=400, detail="Invalid mockup identifier.")
    
    # Validate and parse scene_order JSON.
    try:
        scenes = json.loads(scene_order)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid scene order JSON.")
    
    # Trigger the Celery task to process the job asynchronously.
    task = process_job.delay(mockup_id, scene_order, user_video_path)
    
    return {"job_id": task.id, "message": "Job submitted successfully."}

@router.get("/job-status/{job_id}")
async def job_status(job_id: str):
    try:
        result = AsyncResult(job_id)
        return {"job_id": job_id, "status": result.status, "result": result.result}
    except Exception as e:
        # Log the error as needed.
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_video(filename: str):
    """
    Endpoint to download the final composite video.
    
    Expects:
      - filename: The filename of the final output video (located in uploads/final_outputs).
      
    Returns:
      A FileResponse to download the video.
    """
    file_path = os.path.join("uploads", "final_outputs", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type="video/mp4", filename=filename)



