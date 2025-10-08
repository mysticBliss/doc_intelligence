from __future__ import annotations
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
        self.validate_config()

    def validate_config(self) -> None:
        if not self.config.get("document_types"):
            raise ValueError("DocumentClassifierProcessor requires 'document_types' in config.")
        if not self.config.get("ollama_base_url"):
            raise ValueError("DocumentClassifierProcessor requires 'ollama_base_url' in config.")

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """
        Classifies the document type using the VLM.

        Args:
            payload: The data payload containing the image data.

        Returns:
            A ProcessorResult containing the classification result.
        """
        document_types = self.config["document_types"]
        ollama_base_url = self.config["ollama_base_url"]
        model = self.config.get("model", "llava:latest")
        timeout = self.config.get("timeout", 60.0)

        self.logger.info("document_classifier.process.start", document_types=document_types)

        prompt = f"What type of document is this? Choose from the following options: {', '.join(document_types)}. Respond with only one word."

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "images": [payload.image_data],
                        "stream": False,
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                result = response.json()
                document_type = result.get("response", "").strip().lower()

                if document_type not in document_types:
                    self.logger.warning(
                        "document_classifier.process.unknown_type",
                        classified_type=document_type,
                    )
                    return ProcessorResult(
                        processor_name=self.name,
                        status="failure",
                        error=f"VLM classified the document as '{document_type}', which is not in the list of allowed types.",
                    )

                self.logger.info(
                    "document_classifier.process.success",
                    document_type=document_type,
                )
                return ProcessorResult(
                    processor_name=self.name,
                    status="success",
                    results={"document_type": document_type},
                )

        except httpx.RequestError as e:
            self.logger.error("document_classifier.process.request_error", error=str(e))
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error=f"Failed to connect to VLM service: {str(e)}",
            )
        except Exception as e:
            self.logger.error("document_classifier.process.exception", error=str(e))
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error=f"An unexpected error occurred during document classification: {str(e)}",
            )