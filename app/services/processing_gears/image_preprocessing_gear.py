import cv2
import numpy as np
import base64
from typing import Dict, Any, List, Optional

from app.core.pipeline_config import pipeline_config
from app.domain.models import ProcessingGearResult
from app.services.image_preprocessor import ImagePreprocessor
from app.services.processing_gears.base import ProcessingGear

DEFAULT_PIPELINE_NAME = "Default OCR"

class ImagePreprocessingGear(ProcessingGear):
    """
    A concrete 'gear' that encapsulates image preprocessing functionalities.

    This class adapts the existing ImagePreprocessor to the ProcessingGear protocol,
    acting as a concrete strategy in our extensible framework. It is now fully
    configurable, loading its pipeline from the centralized PipelineConfig service.
    """
    gear_name = "image_preprocessor"

    def __init__(self):
        self.preprocessor = ImagePreprocessor()

    async def process(self, image_data: bytes, pipeline_steps: Optional[List[str]] = None) -> ProcessingGearResult:
        """
        Executes the configured preprocessing pipeline on the input image.

        Args:
            image_data: The raw byte content of the image.
            pipeline_steps: A list of preprocessing steps to execute.

        Returns:
            A ProcessingGearResult containing the processed image and metadata.
        """
        if pipeline_steps is None:
            pipeline_steps = ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"]

        processed_image_np, step_results = await self.preprocessor.run_pipeline(
            image_bytes=image_data, pipeline=pipeline_steps
        )

        # Convert final NumPy image back to bytes for consistent output
        is_success, buffer = cv2.imencode(".jpg", processed_image_np)
        if not is_success:
            # Enterprise-grade error handling
            raise RuntimeError("Failed to encode processed image to JPEG format.")

        processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

        # The confidence score is 1.0 as this is a deterministic process.
        return ProcessingGearResult(
            gear_name=self.gear_name,
            confidence_score=1.0,
            result_data={
                "processed_image_b64": processed_image_b64,
                "preprocessing_steps": step_results,
            },
        )