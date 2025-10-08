from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog

from app.processing.payloads import DocumentPayload, ProcessorResult


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
        # Context attributes to be set by the `execute` method
        self.page_number: Optional[int] = None
        self.parent_document_id: Optional[str] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the processor."""
        pass

    async def execute(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """
        Executes the processor with context, called by the pipeline.
        This method sets the page-level context before calling the `process` method.
        """
        # Set the context for the decorator to use
        self.page_number = payload.page_number
        self.parent_document_id = payload.parent_document_id
        
        # The actual processing is now wrapped and called here
        return await self.process(payload, logger=logger)

    @abstractmethod
    async def process(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """
        Processes the document or data. This method is implemented by each concrete processor.

        Args:
            payload: The DocumentPayload containing the data to process.
            logger: A bound structlog logger for structured, contextual logging.

        Returns:
            A ProcessorResult containing the outcome and any relevant data.
        """
        pass