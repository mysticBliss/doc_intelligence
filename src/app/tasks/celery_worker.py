import asyncio
import structlog
from app.tasks.celery_app import celery
from app.core.dependencies import get_document_orchestration_service

@celery.task
def run_pipeline_task(pipeline_config, file_data, file_name, correlation_id):
    logger = structlog.get_logger()
    service = get_document_orchestration_service()
    service.logger = logger

    async def main():
        return await service.process_document(
            file_data=file_data,
            file_name=file_name,
            pipeline_config=pipeline_config,
            correlation_id=correlation_id,
        )

    result = asyncio.run(main())
    return result.model_dump()