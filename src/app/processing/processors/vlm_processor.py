import base64
import httpx
from app.processing.decorators import instrument_step
from app.processing.payloads import DocumentPayload, ProcessorResult
from app.processing.processors.base import BaseProcessor
from typing import Any, Dict, Optional
import structlog


class VlmProcessor(BaseProcessor):
    name = "vlm_processor"

    def __init__(self, config: Dict[str, Any], ollama_base_url: str, logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.ollama_base_url = ollama_base_url
        self.validate_config()

    def validate_config(self):
        required_params = ["prompt", "model", "temperature", "max_tokens"]
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"'{param}' is a required configuration parameter for VlmProcessor.")

    @instrument_step
    async def process(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """Analyzes the image with a VLM and returns the structured response."""
        prompt = self.config["prompt"]
        model = self.config["model"]
        temperature = self.config["temperature"]
        max_tokens = self.config["max_tokens"]

        image_bytes = base64.b64decode(payload.file_content)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        async with httpx.AsyncClient(timeout=1800.0) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
            )
            response.raise_for_status()  # Raise an exception for bad status codes

        # The actual response content is in response.json()['message']['content']
        analysis_result = response.json().get("message", {}).get("content", "")

        self.logger.info("vlm.processing.finished")

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            output="VLM analysis completed successfully.",
            structured_results={"analysis": analysis_result},
            metadata={"page_number": payload.page_number}
        )