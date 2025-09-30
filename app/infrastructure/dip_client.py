import httpx
import structlog
from pybreaker import CircuitBreaker, CircuitBreakerError
from app.core.config import settings
from app.domain.models import (
    DIPRequest,
    DIPResponse,
    DIPChatRequest,
    DIPChatResponse,
)
from app.domain.ports import DIPClientPort
from fastapi_cache.decorator import cache

logger = structlog.get_logger(__name__)

# Define a circuit breaker for the DIP service
# Fail after 3 consecutive failures, and stay open for 60 seconds
dip_breaker = CircuitBreaker(fail_max=3, reset_timeout=60)

class DIPClient(DIPClientPort):
    def __init__(self, base_url: str):
        self.base_url = base_url

    @dip_breaker
    async def generate(self, request: DIPRequest) -> DIPResponse:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": request.stream,
                }
                if request.images:
                    payload["images"] = request.images

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=settings.DIP_GENERATE_TIMEOUT,
                )
                response.raise_for_status()
                return DIPResponse(**response.json())
        except httpx.TimeoutException as e:
            logger.error("Request to DIP service timed out", exc_info=True)
            raise  # Re-raise to be caught by the circuit breaker
        except httpx.HTTPStatusError as e:
            logger.error(
                "DIP service returned an error",
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except CircuitBreakerError as e:
            logger.error("Circuit breaker is open for DIP service", exc_info=True)
            # Re-raise as a more specific exception if needed, or handle gracefully
            raise 

    @dip_breaker
    async def chat(self, request: DIPChatRequest) -> DIPChatResponse:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": request.model,
                    "messages": [],
                    "stream": request.stream,
                }
                for msg in request.messages:
                    message_payload = {"role": msg.role, "content": msg.content}
                    if msg.annotated_images:
                        message_payload["images"] = [
                            img.image_data for img in msg.annotated_images
                        ]
                    payload["messages"].append(message_payload)

                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=3600.0,
                )
                response.raise_for_status()
                return DIPChatResponse(**response.json())
        except httpx.TimeoutException as e:
            logger.error("Request to DIP chat service timed out", exc_info=True)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "DIP chat service returned an error",
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except CircuitBreakerError as e:
            logger.error("Circuit breaker is open for DIP chat service", exc_info=True)
            raise

def get_dip_client() -> DIPClientPort:
    return DIPClient(base_url=settings.DIP_BASE_URL)