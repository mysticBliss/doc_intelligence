from typing import Protocol, Dict, Any
from app.domain.models import ProcessingGearResult

class ProcessingGear(Protocol):
    """
    Defines the contract for a 'processing gear' using the Strategy Pattern.

    This protocol ensures that any processing component (e.g., for preprocessing,
    OCR, VLM analysis) adheres to a standardized interface, making the system
    pluggable and extensible.
    """
    gear_name: str

    async def process(self, image_data: bytes) -> ProcessingGearResult:
        """
        Processes the given image data and returns a standardized result.

        Args:
            image_data: The raw byte content of the image to be processed.

        Returns:
            A ProcessingGearResult containing the outcome, confidence score,
            and any relevant data.
        """
        ...