from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

from app.core.schemas.base import BaseProcessorConfig
from app.processing.processors.base import ProcessorResult


class PipelineTemplate(BaseModel):
    """A template for a preprocessing pipeline."""
    name: str = Field(..., description="The name of the pipeline template.")
    steps: List[str] = Field(..., description="The sequence of preprocessing steps.")


class BoundingBox(BaseModel):
    """Represents a bounding box with normalized coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float


class AnnotatedImage(BaseModel):
    """Represents an image with optional bounding box annotations."""
    image_data: str  # b64 encoded
    annotations: List[BoundingBox] = []


class StepMetadata(BaseModel):
    """Metadata captured for a single preprocessing step."""
    input_hash: str = Field(..., description="MD5 hash of the input image.")
    output_hash: str = Field(..., description="MD5 hash of the output image.")
    processing_time_ms: float = Field(..., description="Time taken for the step in milliseconds.")
    parameters: Dict[str, Any] = Field({}, description="Parameters used for the step.")


class ProcessingStepResult(BaseModel):
    """Represents the result of a single preprocessing step, including metadata."""
    step_name: str
    input_image: str  # b64 encoded
    output_image: str  # b64 encoded
    metadata: StepMetadata


class DIPRequest(BaseModel):
    model: str
    prompt: str
    images: Optional[List[str]] = None  # For processed, base64-encoded images
    annotated_images: Optional[List[AnnotatedImage]] = None
    stream: bool = False


class DIPResponse(BaseModel):
    model: str
    created_at: str
    response: str
    done: bool
    request_context: Optional["RequestContext"] = None
    # The outer list corresponds to pages, the inner list to processing steps for that page.
    processing_results: Optional[List[List[ProcessingStepResult]]] = None
    document_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    annotated_images: Optional[List[AnnotatedImage]] = None


class DIPChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False


class DIPChatResponse(BaseModel):
    model: str
    created_at: str
    message: ChatMessage
    done: bool
    metadata: Optional["DocumentMetadata"] = None
    request_context: Optional["RequestContext"] = None


class PageMetadata(BaseModel):
    page_number: int
    image_size_bytes: int
    image_format: str
    image_dimensions: tuple[int, int]


class DocumentMetadata(BaseModel):
    file_name: str
    file_size_bytes: int
    page_count: int
    pages: List[PageMetadata]


class RequestContext(BaseModel):
    correlation_id: str = Field(..., description="The correlation ID for the request.")


class AuditEventName(str, Enum):
    """Enum for audit event names to ensure consistency."""

    PROCESS_PDF_SUCCESS = "process_pdf_success"
    PROCESS_PDF_FAILURE = "process_pdf_failure"


class AuditEvent(BaseModel):
    """
    Pydantic model for a structured audit event.

    This model captures key information about a request and its outcome,
    which is crucial for auditing, analytics, and debugging.
    """

    event_name: AuditEventName
    correlation_id: str
    timestamp: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    http_method: str
    endpoint_path: str
    http_status_code: int
    response_time_ms: float
    # Using Dict[str, Any] for flexibility, but in a real system,
    # this could be a more specific Pydantic model.
    event_data: Dict[str, Any]

class ChatRequest(BaseModel):
    prompt: str



class JobStatus(str, Enum):
    """Enum for job status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"





class DocumentProcessingRequest(BaseModel):
    image_base64: str
    processors: List[str]
    document_id: Optional[str] = None
    preprocessing_steps: List[str] = []
    prompt: Optional[str] = None


class DocumentProcessingResult(BaseModel):
    """
    Aggregates the results from all processors in a single workflow.

    This model serves as the comprehensive output of the
    `DocumentOrchestrationService`. It contains the full list of processor
    results and a correlation ID, enabling end-to-end traceability of the
    entire processing request.
    """
    results: List[ProcessorResult]
    correlation_id: str


class DocumentProcessingResponse(BaseModel):
    """
    Defines the final API response structure for a document processing request.

    This model is the public data contract for the `/documents/process`
    endpoint. It presents the processing results and correlation ID in a
    clear, client-friendly format, abstracting away the internal
    implementation details of the orchestration service.
    """
    results: List[ProcessorResult]
    correlation_id: str

class JobCreationResponse(BaseModel):
    """Response for a job creation request."""
    job_id: str




class JobStatusResponse(BaseModel):
    """Response for a job status request."""
    status: JobStatus
    result: Optional[DocumentProcessingResponse] = None
    error: Optional[str] = None


class VLMResponse(BaseModel):
    vlm_response: str