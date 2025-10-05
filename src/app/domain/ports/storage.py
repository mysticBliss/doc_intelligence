from typing import Protocol, IO

class StoragePort(Protocol):
    """Port for a storage service."""

    def save_file(self, file_name: str, file_data: IO[bytes], content_type: str) -> str:
        """Save a file to the storage service."""
        ...

    def get_file_url(self, file_name: str) -> str:
        """Get the URL of a file in the storage service."""
        ...