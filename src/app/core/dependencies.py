import os
from functools import lru_cache

from app.infrastructure.storage.minio_adapter import MinIOStorageAdapter
from app.domain.ports.storage import StoragePort
from app.services.preprocessing_service import PreprocessingService
from app.infrastructure.dip_client import DIPClient
from app.processing.factory import ProcessorFactory
from app.services.document_orchestration_service import DocumentOrchestrationService

@lru_cache()
def get_storage_service() -> StoragePort:
    """Get the storage service."""
    return MinIOStorageAdapter(
        endpoint=os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
    )

@lru_cache()
def get_processor_factory() -> ProcessorFactory:
    return ProcessorFactory()

def get_document_orchestration_service(
) -> DocumentOrchestrationService:
    return DocumentOrchestrationService(
        storage_port=get_storage_service(), factory=get_processor_factory()
    )

@lru_cache()
def get_preprocessing_service() -> PreprocessingService:
    """Get the preprocessing service."""
    return PreprocessingService()

@lru_cache()
def get_dip_client() -> DIPClient:
    """Get the DIP client."""
    return DIPClient(base_url=os.environ["OLLAMA_BASE_URL"])