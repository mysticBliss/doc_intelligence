from typing import List, Optional, Any, Dict, Literal
from pydantic import BaseModel


class DocumentPayload(BaseModel):
    """
    Represents the data payload passed between processors in a pipeline.

    This model serves as a standardized data contract, ensuring that each
    processor receives the information it needs in a consistent format. It is
    designed to be extensible, allowing new fields to be added as the
    application's requirements evolve.
    """
    image_data: str  # Base64-encoded image data
    results: List[Dict[str, Any]] = [] # To store results from previous steps


class ProcessorResult(BaseModel):
    """Represents the result of a processor execution."""
    processor_name: str
    status: Literal["success", "failure"]
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class StepMetadata(BaseModel):
    pass


class ProcessingStepResult(BaseModel):
    step_name: str
    input_image: str
    output_image: str
    metadata: StepMetadata


class ImagePreprocessingResult(BaseModel):
    final_image: str
    steps: List[ProcessingStepResult]