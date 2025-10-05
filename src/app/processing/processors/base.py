from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel

from app.processing.payloads import ProcessorResult


class BaseProcessor(ABC):
    """
    Abstract base class defining the contract for all processors.

    This enforces the Strategy Pattern, ensuring that every processor adheres to a
    standardized interface. It isolates the pipeline execution logic from the
    specific implementation details of each processing step.
    """

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        self.config = config
        self.logger = logger.bind(processor_name=self.name)

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the processor."""
        pass

    @abstractmethod
    async def process(self, *, logger: structlog.stdlib.BoundLogger, **kwargs: Any) -> ProcessorResult:
        """
        Processes the document or data.

        Args:
            logger: A bound structlog logger for structured, contextual logging.
            **kwargs: The data to be processed, which may vary by processor.

        Returns:
            A ProcessorResult containing the outcome and any relevant data.
        """
        pass