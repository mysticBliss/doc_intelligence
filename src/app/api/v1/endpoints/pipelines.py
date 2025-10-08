import uuid
from typing import List, Union
from pathlib import Path
import json
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Response

from app.core.dependencies import get_document_orchestration_service
from app.services.document_orchestration_service import DocumentOrchestrationService
from app.tasks.celery_app import celery
from app.tasks.celery_worker import run_pipeline_task

from app.api.v1.schemas.schemas import DocumentProcessingResult, JobCreationResponse, JobStatusResponse
from app.core.schemas.enums import JobStatus

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
    service.logger.info("Starting synchronous pipeline", pipeline_name=pipeline_name, correlation_id=correlation_id)
    result = await service.process_document(
        file_data=file_data,
        file_name=file.filename,
        pipeline_config=config,
        correlation_id=correlation_id,
    )
    service.logger.info("Synchronous pipeline finished", pipeline_name=pipeline_name, correlation_id=correlation_id)
    return result

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_task_status(job_id: str, service: DocumentOrchestrationService = Depends(get_document_orchestration_service)):
    """
    Retrieves the status of a Celery task by Celery task ID, handling different states:
    - PENDING/RETRY: The task is in progress.
    - SUCCESS: The task completed. The business outcome is in the result payload.
    - FAILURE: The task failed due to an unhandled exception. The error is in the result.
    """
    try:
        service.logger.info("Checking task status for job_id", job_id=job_id)
        task = celery.AsyncResult(job_id)
        task_state = task.state
        service.logger.info("Retrieved task state", job_id=job_id, task_state=task_state)

        if task_state == 'PENDING' or task_state == 'RETRY':
            service.logger.info("Task is in progress.", job_id=job_id, task_state=task_state)
            return JobStatusResponse(status=JobStatus.IN_PROGRESS)

        elif task_state == 'SUCCESS':
            service.logger.info("Task completed successfully.", job_id=job_id)
            result_data = task.result

            # Log the result structure for debugging
            service.logger.info("Task result structure", job_id=job_id, result_type=type(result_data).__name__, result_preview=str(result_data)[:200])

            if isinstance(result_data, str):
                # The worker serializes the result, so we deserialize the JSON string here.
                processing_result = DocumentProcessingResult.model_validate_json(result_data)
                return JobStatusResponse(status=JobStatus.SUCCESS, result=processing_result)
            elif isinstance(result_data, dict):
                # Check if the result is wrapped in a 'result' key (from meta)
                if 'result' in result_data and isinstance(result_data['result'], str):
                    # Extract the JSON string from the meta wrapper
                    processing_result = DocumentProcessingResult.model_validate_json(result_data['result'])
                    return JobStatusResponse(status=JobStatus.SUCCESS, result=processing_result)
                else:
                    # Handle old format for backward compatibility
                    return JobStatusResponse(status=JobStatus.SUCCESS, result=DocumentProcessingResult(**result_data))
            else:
                service.logger.error("Task succeeded but result format is invalid.", job_id=job_id, result_type=type(result_data).__name__)
                return JobStatusResponse(status=JobStatus.FAILED, error="Task succeeded, but the result format was invalid.")

        elif task_state == 'FAILURE':
            service.logger.error("Task failed with an exception.", job_id=job_id, info=str(task.info), task_result=str(task.result))
            return JobStatusResponse(status=JobStatus.FAILED, error=str(task.info))

        service.logger.warning("Task in an unexpected state.", job_id=job_id, task_state=task_state)
        return JobStatusResponse(status=JobStatus.FAILED, error=f"Task is in an unexpected state: {task_state}")

    except Exception as e:
        service.logger.error(
            "Failed to decode Celery task result",
            job_id=job_id,
            error=str(e),
            task_state=task_state,
            result_type=type(task.result).__name__ if hasattr(task, 'result') else 'unknown',
            result_preview=str(task.result)[:200] if hasattr(task, 'result') else 'no result',
            exc_info=True
        )
        return JobStatusResponse(
            status=JobStatus.FAILED,
            error=f"Failed to retrieve task status: {str(e)}. Task state: {task_state}. Please check logs for details."
        )

    except Exception as e:
        service.logger.error(
            "Unexpected error in get_task_status",
            job_id=job_id,
            error=str(e),
            exc_info=True
        )
        return JobStatusResponse(
            status=JobStatus.FAILED,
            error=f"Unexpected error retrieving task status: {str(e)}"
        )