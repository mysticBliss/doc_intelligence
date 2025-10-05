from app.domain.ports.dip_client_port import DIPClientPort


class MockDIPClient(DIPClientPort):
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def generate(self, model: str, prompt: str) -> dict:
        return {"response": "test"}