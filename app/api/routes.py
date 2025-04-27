import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, Header
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from app.tasks.processing_tasks import process_video
from app.config import load_mockup_config  # A helper function to load your mockups configuration
from app.config.logging import get_logger
from app.services.storage import storage
from app.config.exceptions import APIError

router = APIRouter()

# API Key validation
async def verify_token(x_api_key: str = Header(None)) -> None:
    """Verify the API key from the X-API-Key header."""
    if not x_api_key or x_api_key != os.getenv("API_KEY"):
        raise APIError(
            status_code=401,
            error_code="UNAUTHORIZED",
            detail="Invalid or missing API key"
        )

@router.post("/templates", dependencies=[Depends(verify_token)])
async def upload_template(
    template_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload or update a template manifest.
    
    Expects:
      - template_id: Identifier for the template
      - file: The mockups.json manifest file
    """
    try:
        # Validate JSON content
        content = await file.read()
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise APIError(
                status_code=400,
                error_code="INVALID_JSON",
                detail="Invalid JSON content"
            )
        
        # Save to MinIO
        object_name = f"templates/{template_id}/mockups.json"
        temp_path = f"/tmp/{uuid.uuid4()}.json"
        
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            storage.put_object(object_name, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return {"message": "Template uploaded successfully"}
    except Exception as e:
        raise APIError(
            status_code=500,
            error_code="TEMPLATE_UPLOAD_ERROR",
            detail=str(e)
        )

@router.get("/templates")
async def list_templates():
    """List available templates."""
    try:
        config = load_mockup_config()
        return {
            "templates": [
                {
                    "id": template_id,
                    "scenes": len(template["scenes"]),
                    "thumbnail": template.get("thumbnail_url")
                }
                for template_id, template in config.items()
            ]
        }
    except Exception as e:
        raise APIError(
            status_code=500,
            error_code="TEMPLATE_LIST_ERROR",
            detail=str(e)
        )

@router.post("/submit-job", dependencies=[Depends(verify_token)])
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
    # Save the uploaded user video to MinIO
    object_name = f"uploads/{uuid.uuid4()}.mp4"
    temp_path = f"/tmp/{uuid.uuid4()}.mp4"
    
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        video_key = storage.put_object(object_name, temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Load mockup configuration.
    config = load_mockup_config()
    if mockup_id not in config:
        raise APIError(
            status_code=400,
            error_code="INVALID_MOCKUP",
            detail="Invalid mockup identifier"
        )
    
    # Validate and parse scene_order JSON.
    try:
        scenes = json.loads(scene_order)
    except json.JSONDecodeError:
        raise APIError(
            status_code=400,
            error_code="INVALID_SCENE_ORDER",
            detail="Invalid scene order JSON"
        )
    
    task = process_video.delay(
        mockup_id=mockup_id,
        scene_order_json=scene_order,
        video_key=video_key
    )
    
    return {"job_id": task.id, "message": "Job submitted successfully"}

@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a processing job."""
    task_result = AsyncResult(job_id)
    
    if task_result.ready():
        if task_result.successful():
            result = task_result.get()
            # Generate presigned URL for the final video
            download_url = storage.get_presigned_url(result["output_path"])
            return {
                "status": "SUCCESS",
                "download_url": download_url
            }
        else:
            return {
                "status": "FAILURE",
                "error": str(task_result.result)
            }
    else:
        return {
            "status": "PROGRESS",
            "meta": task_result.info
        }

@router.get("/download/{filename}")
async def download_video(filename: str):
    """
    Endpoint to download the final composite video.
    
    Expects:
      - filename: The filename of the final output video (located in uploads/final).
      
    Returns:
      A FileResponse to download the video.
    """
    file_path = os.path.join("uploads", "final", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type="video/mp4", filename=filename)

@router.get("/api/templates/{template_id}")
async def get_template(template_id: str, request: Request):
    """Get template configuration by ID."""
    config = load_mockup_config()
    if template_id not in config:
        logger = get_logger(correlation_id=request.headers.get("X-Correlation-ID", str(uuid.uuid4())))
        logger.error("template_not_found", template_id=template_id)
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return config[template_id]



