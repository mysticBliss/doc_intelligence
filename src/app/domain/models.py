from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


from app.core.schemas.base import BaseProcessorConfig
from app.core.schemas.enums import JobStatus





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










class VLMResponse(BaseModel):
    vlm_response: str