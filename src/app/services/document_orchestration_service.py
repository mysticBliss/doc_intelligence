import base64
from typing import Any, Dict, Optional
import structlog
import time
from app.api.v1.schemas.schemas import DocumentProcessingResult
from app.core.logging import LoggerRegistry
from app.domain.ports.storage import StoragePort
import hashlib
from io import BytesIO
from app.processing.pipeline import ProcessingPipeline
from app.processing.payloads import DocumentPayload
from app.processing.factory import ProcessorFactory


class DocumentOrchestrationService:
    """
    Orchestrates the entire document processing workflow, from receiving the
    initial request to executing a series of processors and aggregating their
    results.

    This service embodies the core business logic of the document intelligence
    platform, adhering to enterprise patterns like Dependency Injection and
    the Factory pattern for a modular and extensible architecture.
    """

    def __init__(self, storage_port: StoragePort, factory: ProcessorFactory, logger: Optional[structlog.stdlib.BoundLogger] = None):
        """
        Initializes the service with a storage port, a processor factory, and a
        structured logger.

        Args:
            storage_port: The storage port for saving and retrieving files.
            factory: The factory for creating processor instances.
            logger: A logger instance, typically injected with request-specific
                    context like a correlation ID. If not provided, a default
                    logger is created.
        """
        self.storage_port = storage_port
        self.factory = factory
        self.logger = logger or LoggerRegistry.get_service_logger("orchestration")

    async def process_document(
        self,
        file_data: bytes,
        file_name: str,
        pipeline_config: Dict[str, Any],
        correlation_id: str,
    ) -> DocumentProcessingResult:
        """
        Asynchronously processes a document through a pipeline of processors.

        This method serves as the central entry point for all document
        processing tasks. It dynamically instantiates the required processors,
        executes them in sequence, and returns a structured result.

        Args:
            file_data: The raw byte content of the document to be processed.
            file_name: The name of the file to be processed.
            processor_names: A list of string identifiers for the processors
                             to be executed.
            processor_params: A dictionary of parameters to be passed to the
                              processors.
            correlation_id: A unique identifier for tracing the request across
                            services.

        Returns:
            A `DocumentProcessingResult` object containing the outcomes of each
            processing step.
        """
        start_time = time.time()
        log = self.logger.bind(
            correlation_id=correlation_id,
            pipeline_config=pipeline_config,
        )
        log.info("Starting document processing orchestration")

        # Generate a unique ID for the document
        document_id = hashlib.md5(file_data).hexdigest()
        file_name = f"{document_id}_{file_name}"

        # Save the file to storage
        try:
            file_url = self.storage_port.save_file(file_name, BytesIO(file_data), "application/octet-stream")
            log.info(f"File saved to storage: {file_url}")
        except Exception as e:
            log.exception("Failed to save file to storage")
            return DocumentProcessingResult(
                results={},
                correlation_id=correlation_id,
            )



        pipeline = ProcessingPipeline(pipeline_config, self.factory)
        initial_payload = DocumentPayload(
            file_content=file_data, 
            file_name=file_name,
            document_id=document_id,
            job_id=correlation_id  # Pass the correlation_id as the job_id
        )

        log.info("Starting pipeline execution...")
        final_result = await pipeline.run(initial_payload, logger=log)
        log.info("Pipeline execution finished.", status=final_result.status.value)

        final_status = final_result.status.value
        self.logger.info(
            "Pipeline execution finished",
            correlation_id=correlation_id,
            pipeline_name=pipeline_config.get("name", "unknown"),
            document_id=document_id,
            duration_ms=(time.time() - start_time) * 1000,
            final_status=final_status,
        )

        return final_result