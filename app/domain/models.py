from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum



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

class PipelineTemplate(BaseModel):
    """Represents a named preprocessing pipeline configuration."""
    name: str
    description: str
    steps: List[str]

# --- New Models for Extensible Processing Framework ---

class ProcessingGearResult(BaseModel):
    """Standardized result from a single processing gear."""
    gear_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    result_data: Dict[str, Any]

class ImageProcessingRequest(BaseModel):
    """Request to process a single image with a specified set of gears."""
    image_data: str  # b64 encoded
    gears_to_run: List[str]
    preprocessing_steps: Optional[List[str]] = None
    pipeline_name: str = "Default OCR"
    document_id: Optional[str] = None

class ImageProcessingResponse(BaseModel):
    """Aggregated results from running multiple gears on an image."""
    image_id: str
    original_image_hash: str
    results: List[ProcessingGearResult]