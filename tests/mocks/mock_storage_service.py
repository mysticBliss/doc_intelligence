from app.domain.ports.storage import StoragePort


class MockStorageService(StoragePort):
    async def save(self, file_name: str, file_data: bytes) -> str:
        return f"mock_path/{file_name}"