import httpx
from app.domain.ports.dip_client_port import DIPClientPort


class DIPClient(DIPClientPort):
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def generate(self, model: str, prompt: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt},
            )
            response.raise_for_status()
            return response.json()