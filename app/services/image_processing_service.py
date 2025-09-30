import base64
import hashlib
import concurrent.futures

from app.domain.models import ImageProcessingRequest, ImageProcessingResponse, ProcessingGearResult
from app.services.gear_factory import create_gears
import structlog
import asyncio
from typing import List, Optional, Tuple

logger = structlog.get_logger(__name__)

class ImageProcessingService:
    """
    Orchestrates the execution of a dynamic pipeline of processing gears.

    This service is the core of our Hexagonal Architecture, representing the
    application's primary business logic, completely decoupled from the API layer.
    """

    async def process_image(self, request: ImageProcessingRequest) -> ImageProcessingResponse:
        """
        Processes a single image using a dynamically selected set of gears.
        """
        log_context = {"gears_to_run": request.gears_to_run}
        if request.document_id:
            log_context["document_id"] = request.document_id

        logger.info("Received request to process image", **log_context)

        try:
            image_data = base64.b64decode(request.image_data)
            image_id = hashlib.md5(image_data).hexdigest()
            log_context["image_id"] = image_id

            # Simplified gear creation, removing the problematic config
            gear_configs = {gear_name: {} for gear_name in request.gears_to_run}
            gears = create_gears(gear_configs)

            # Pass preprocessing_steps to the process method
            tasks = [
                gear.process(image_data, pipeline_steps=request.preprocessing_steps)
                for gear in gears
            ]
            results: list[ProcessingGearResult] = await asyncio.gather(*tasks)

            response = ImageProcessingResponse(
                image_id=image_id,
                original_image_hash=image_id, # Using the same hash for simplicity
                results=results,
            )

            logger.info("Image processing completed successfully", **log_context)
            return response

        except Exception as e:
            logger.error(
                "An error occurred during image processing",
                exc_info=True,
                **log_context,
            )
            raise