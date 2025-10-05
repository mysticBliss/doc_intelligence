import base64
import httpx
from app.processing.decorators import instrument_step
from app.processing.payloads import DocumentPayload, ProcessorResult
from app.processing.processors.base import BaseProcessor, ProcessorResult
from typing import Any, Dict
import structlog


class VlmProcessor(BaseProcessor):
    name = "vlm_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.validate_config()
        self._check_ollama_health()

    def _check_ollama_health(self):
        ollama_base_url = self.config.get("ollama_base_url", "http://ollama:11434")
        try:
            httpx.get(f"{ollama_base_url}/api/tags")
            self.logger.info("Ollama service is healthy.")
        except httpx.RequestError as e:
            self.logger.error("Ollama service is unreachable.", error=str(e))
            raise RuntimeError("Ollama service is unreachable.") from e

    def validate_config(self):
        if "model" not in self.config:
            self.config["model"] = "qwen2.5vl:3b"
        if "temperature" not in self.config:
            self.config["temperature"] = 0.7
        if "max_tokens" not in self.config:
            self.config["max_tokens"] = 1024

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """Analyzes the image with a VLM and returns the structured response."""
        prompt = self.config.get("prompt", "What is in this image?")
        ollama_base_url = self.config.get("ollama_base_url", "http://ollama:11434")
        model = self.config.get("model")
        temperature = self.config.get("temperature")
        max_tokens = self.config.get("max_tokens")

        if isinstance(payload.image_data, bytes):
            image_b64 = base64.b64encode(payload.image_data).decode("utf-8")
        else:
            image_b64 = payload.image_data

        async with httpx.AsyncClient(timeout=1800.0) as client:
            response = await client.post(
                f"{ollama_base_url}/api/chat",
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

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            results={"analysis": analysis_result},
        )