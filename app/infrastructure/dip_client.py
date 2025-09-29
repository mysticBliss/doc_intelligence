import httpx
from core.config import settings
from domain.models import (
    DIPRequest,
    DIPResponse,
    DIPChatRequest,
    DIPChatResponse,
)
from fastapi_cache.decorator import cache

class DIPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    @cache(expire=600)  # Cache for 10 minutes
    async def generate(self, request: DIPRequest) -> DIPResponse:
        async with httpx.AsyncClient() as client:
            # Manually construct the payload to ensure correct format for the external API
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

    @cache(expire=600)  # Cache for 10 minutes
    async def chat(self, request: DIPChatRequest) -> DIPChatResponse:
        async with httpx.AsyncClient() as client:
            # Manually construct the payload to handle the nested structure
            payload = {
                "model": request.model,
                "messages": [],
                "stream": request.stream,
            }
            for msg in request.messages:
                message_payload = {"role": msg.role, "content": msg.content}
                if msg.annotated_images:
                    # Extract just the image data for the external API
                    message_payload["images"] = [
                        img.image_data for img in msg.annotated_images
                    ]
                payload["messages"].append(message_payload)

            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=3600.0,  # Increased timeout for potentially long-running vision models
            )
            response.raise_for_status()
            return DIPChatResponse(**response.json())

def get_dip_client() -> DIPClient:
    return DIPClient(base_url=settings.DIP_BASE_URL)