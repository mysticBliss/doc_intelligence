
import base64
from typing import Any, Dict, List

import httpx
import structlog

from app.processing.decorators import instrument_step
from app.processing.processors.base import BaseProcessor, ProcessorResult
from app.processing.payloads import DocumentPayload


class DocumentClassifierProcessor(BaseProcessor):
    name = "document_classifier_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """
        Classifies the document type using the VLM.

        Args:
            payload: The data payload containing the image data.
            logger: A structured logger.

        Returns:
            A ProcessorResult containing the classification result.
        """
        document_types = self.config.get("document_types", [])
        log = logger.bind(
            processor_name=self.processor_name, document_types=document_types
        )
        log.info("document_classifier.process.start")

        prompt = f"What type of document is this? Choose from the following options: {', '.join(document_types)}. Respond with only one word."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://ollama:11434/api/generate",
                    json={
                        "model": "llava:latest",
                        "prompt": prompt,
                        "images": [payload.image_data],
                        "stream": False,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                result = response.json()
                document_type = result.get("response", "").strip().lower()

                if document_type not in document_types:
                    log.warning(
                        "document_classifier.process.unknown_type",
                        classified_type=document_type,
                    )
                    return ProcessorResult(
                        processor_name=self.processor_name,
                        successful=False,
                        error=f"VLM classified the document as '{document_type}', which is not in the list of allowed types.",
                    )

                log.info(
                    "document_classifier.process.success",
                    document_type=document_type,
                )
                return ProcessorResult(
                    processor_name=self.processor_name,
                    successful=True,
                    result={"document_type": document_type},
                )

        except httpx.RequestError as e:
            log.error("document_classifier.process.request_error", error=str(e))
            return ProcessorResult(
                processor_name=self.processor_name,
                successful=False,
                error=f"Failed to connect to VLM service: {str(e)}",
            )
        except Exception as e:
            log.error("document_classifier.process.exception", error=str(e))
            return ProcessorResult(
                processor_name=self.processor_name,
                successful=False,
                error=f"An unexpected error occurred during document classification: {str(e)}",
            )