from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

from app.core.schemas.enums import JobStatus

class DocumentProcessingResult(BaseModel):
    job_id: str
    status: JobStatus
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = []
    final_output: Optional[Dict[str, Any]] = None

class PipelineTemplate(BaseModel):
    """A template for a preprocessing pipeline."""
    name: str = Field(..., description="The name of the pipeline template.")
    steps: List[str] = Field(..., description="The sequence of preprocessing steps.")


class JobCreationResponse(BaseModel):
    """Response for a job creation request."""
    job_id: str


class JobStatusResponse(BaseModel):
    """
    Provides the status of an asynchronous job, including the final result if
    the job has completed successfully.

    This model is used by the `/status/{job_id}` endpoint to communicate the
    state of a background processing task. It now accommodates the new
    document-centric result structure.
    """
    status: JobStatus
    result: Optional[DocumentProcessingResult] = None
    error: Optional[str] = None

class DocumentProcessingRequest(BaseModel):
    image_base64: str
    processors: List[str]
    document_id: Optional[str] = None
    preprocessing_steps: List[str] = []
    prompt: Optional[str] = None