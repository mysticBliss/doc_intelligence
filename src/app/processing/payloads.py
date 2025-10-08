from typing import List, Optional, Any, Dict, Literal
from pydantic import BaseModel, Field
from app.core.schemas.enums import JobStatus


class DocumentPayload(BaseModel):
    """
    Represents the data payload passed between processors in a pipeline.
    This model serves as a standardized data contract, ensuring that each
    processor receives the information it needs in a consistent format.
    """
    file_content: bytes
    file_name: str
    job_id: str
    document_id: Optional[str] = Field(None, description="The unique ID for this specific document or image being processed.")
    parent_document_id: Optional[str] = Field(None, description="The unique ID of the original parent document, if applicable.")
    page_number: Optional[int] = Field(None, description="The page number of this image within the parent document.")
    image_data: Optional[str] = None
    results: List[Dict[str, Any]] = Field([], description="A list to store and pass results from previous steps.")

    class Config:
        arbitrary_types_allowed = True


class ProcessorResult(BaseModel):
    """Represents the result of a single processor's execution."""
    processor_name: str
    status: Literal["success", "failure", "skipped"]
    output: Optional[str] = Field(None, description="A simple, human-readable string summary of the result, primarily for logging.")
    structured_results: Optional[Dict[str, Any]] = Field(None, description="The rich, structured, machine-readable data product of the processor.")
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field({}, description="Additional metadata, such as page number.")

class StepMetadata(BaseModel):
    """Metadata captured for a single, instrumented sub-step within a processor."""
    step_name: str
    execution_time_ms: int
    parameters: Dict[str, Any]
    input_hash: str
    output_hash: str


class ProcessingStepResult(BaseModel):
    """The result of an individual image manipulation step."""
    step_name: str
    input_image: str
    output_image: str
    metadata: StepMetadata


class ImagePreprocessingResult(BaseModel):
    """The final result of the entire ImagePreprocessingProcessor pipeline."""
    final_image: str
    steps: List[ProcessingStepResult]