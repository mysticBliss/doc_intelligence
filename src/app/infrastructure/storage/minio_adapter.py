from io import BytesIO
from minio import Minio
from minio.error import S3Error

from app.domain.ports.storage import StoragePort

class MinIOStorageAdapter(StoragePort):
    """Adapter for MinIO storage."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def save_file(self, file_name: str, file_data: BytesIO, content_type: str) -> str:
        """Save a file to MinIO."""
        try:
            bucket_name = "documents"
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

            file_data.seek(0)
            self.client.put_object(
                bucket_name,
                file_name,
                file_data,
                length=-1, # Required for streams
                part_size=10*1024*1024, # 10MB part size
                content_type=content_type
            )
            return self.get_file_url(file_name)
        except S3Error as exc:
            raise ConnectionError(f"Error saving file to MinIO: {exc}") from exc

    def get_file_url(self, file_name: str) -> str:
        """Get the URL of a file in MinIO."""
        try:
            bucket_name = "documents"
            return self.client.presigned_get_object(bucket_name, file_name)
        except S3Error as exc:
            raise FileNotFoundError(f"File not found in MinIO: {exc}") from exc