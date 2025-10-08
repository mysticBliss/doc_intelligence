import asyncio
import structlog
from app.tasks.celery_app import celery
from app.core.dependencies import get_document_orchestration_service
from app.core.logging import LoggerRegistry


@celery.task(bind=True)
def run_pipeline_task(self, pipeline_config, file_data, file_name, correlation_id):
    logger = LoggerRegistry.get_infrastructure_logger("celery")
    service = get_document_orchestration_service()
    service.logger = logger

    # Log the mapping between Celery task ID and correlation ID for debugging
    logger.info(
        "Celery task started",
        celery_task_id=self.request.id,
        correlation_id=correlation_id,
        pipeline_name=pipeline_config.get("name", "unknown")
    )

    async def main():
        return await service.process_document(
            file_data=file_data,
            file_name=file_name,
            pipeline_config=pipeline_config,
            correlation_id=correlation_id,
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = None

    try:
        result = loop.run_until_complete(main())

        logger.info(
            "Pipeline execution completed successfully",
            celery_task_id=self.request.id,
            correlation_id=correlation_id,
            job_id=result.job_id,
            status=result.status.value
        )

        # Return the result for Celery backend storage
        # Celery will automatically set the state to SUCCESS when the task returns normally
        return result.model_dump_json()

    except Exception:
        logger.exception(
            "Celery task failed unexpectedly",
            celery_task_id=self.request.id,
            correlation_id=correlation_id
        )
        # Update Celery state to FAILURE
        self.update_state(
            state='FAILURE',
            meta={'error': 'Pipeline execution failed', 'result': result.model_dump_json()} if result else {'error': 'Pipeline execution failed'}
        )
        # Re-raise to let Celery handle the failure
        raise

    finally:
        loop.close()