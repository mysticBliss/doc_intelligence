import uuid
from typing import List, Union
from pathlib import Path
import json
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Response

from app.core.dependencies import get_document_orchestration_service
from app.services.document_orchestration_service import DocumentOrchestrationService
from app.tasks.celery_app import celery
from app.tasks.celery_worker import run_pipeline_task

from app.domain.models import DocumentProcessingResult, JobCreationResponse

router = APIRouter()

from app.core.pipeline_config import pipeline_config


@router.post("/run", response_model=Union[DocumentProcessingResult, JobCreationResponse])
async def run_pipeline(
    response: Response,
    file: UploadFile = File(...),
    pipeline_name: str = Form(...),
    service: DocumentOrchestrationService = Depends(get_document_orchestration_service),
    correlation_id: str = str(uuid.uuid4()),
):
    """
    Runs a document processing pipeline based on a JSON template.
    The execution mode (sync or async) is determined by the 'execution_mode' key in the template.
    """
    config = pipeline_config.get_pipeline_config(pipeline_name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found.")

    file_data = await file.read()

    execution_mode = config.get("execution_mode", "simple")

    if execution_mode == "dag":  # Asynchronous execution
        # Use .delay() for Celery tasks
        task = run_pipeline_task.delay(
            pipeline_config=config,
            file_data=file_data,
            file_name=file.filename,
            correlation_id=correlation_id,
        )
        return JobCreationResponse(job_id=task.id)
    
    # Synchronous execution for "simple" mode
    service.logger.info(f"Starting synchronous pipeline '{pipeline_name}'...")
    result = await service.process_document(
        file_data=file_data,
        file_name=file.filename,
        pipeline_config=config,
        correlation_id=correlation_id,
    )
    service.logger.info(f"Synchronous pipeline '{pipeline_name}' finished.")
    return result

@router.get("/status/{job_id}")
def get_task_status(job_id: str):
    task = celery.AsyncResult(job_id)
    if task.state == 'PENDING':
        response = {
            "state": task.state,
            "status": "Pending..."
        }
    elif task.state != 'FAILURE':
        response = {
            "state": task.state,
            "status": task.info.get('status', '') if isinstance(task.info, dict) else '',
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {
            "state": task.state,
            "status": str(task.info),  # This is the exception raised
        }
    return response