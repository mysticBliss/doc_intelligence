import base64
import functools
import hashlib
import time
from typing import Any, Callable, Coroutine, Tuple

import numpy as np
import structlog

from app.core.redis import redis_client
from app.processing.payloads import ProcessingStepResult, StepMetadata
from app.processing.processors.base import BaseProcessor, ProcessorResult
import asyncio


def instrument_step(
    func: Callable[..., Coroutine[Any, Any, ProcessorResult]]
) -> Callable[..., Coroutine[Any, Any, ProcessorResult]]:
    """
    A decorator for instrumenting a processor's `process` method.

    This decorator standardizes cross-cutting concerns for all processors:
    - Binds the processor name to the logger for contextual logging.
    - Measures and logs the execution time of the step.
    - Catches and logs any exceptions, wrapping them in a standardized
      `ProcessorResult` for graceful failure handling.
    - Ensures a consistent data contract for observability.

    Args:
        func: The async `process` method to be wrapped.

    Returns:
        The wrapped async method.
    """

    @functools.wraps(func)
    async def wrapper(self: BaseProcessor, *args, **kwargs: Any) -> ProcessorResult:
        log = kwargs.get('logger', structlog.get_logger()).bind(processor_name=self.name)
        kwargs['logger'] = log  # Ensure the logger is in kwargs for the wrapped function
        log.info(f"{self.name}.start")
        start_time = time.perf_counter()
        job_id = kwargs.get('job_id')

        try:
            # Publish initial status
            if job_id:
                await redis_client.publish(f"job:{job_id}", "IN_PROGRESS")

            # Execute the actual processor logic
            result = await func(self, *args, **kwargs)

            # Ensure the result from the processor is valid
            if not isinstance(result, ProcessorResult):
                raise TypeError(
                    f"Processor '{self.name}' did not return a ProcessorResult instance."
                )

            duration_ms = round((time.perf_counter() - start_time) * 1000)
            log.info(f"{self.name}.finished", duration_ms=duration_ms, status=result.status)

            # Augment the result with timing info
            if result.results is not None:
                result.results["_execution_time_ms"] = duration_ms

            # Publish final status
            if job_id:
                await redis_client.publish(f"job:{job_id}", str(result.status.value))

            return result

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000)
            log.error(
                f"{self.name}.failed",
                error=str(e),
                exc_info=True,
                duration_ms=duration_ms,
            )

            # Publish failure status
            if job_id:
                await redis_client.publish(f"job:{job_id}", "FAILURE")

            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error_message=f"An unexpected error occurred in {self.name}: {str(e)}",
            )

    return wrapper


def instrument_sub_step(
    func: Callable[..., Coroutine[Any, Any, np.ndarray]]
) -> Callable[..., Coroutine[Any, Any, Tuple[np.ndarray, ProcessingStepResult]]]:
    """
    Decorator to instrument an image processing sub-step, capturing metadata
    such as timing, image hashes, and parameters. This is intended for functions
    within a processor that perform a distinct part of a larger workflow.

    Args:
        func: The async sub-step function to be wrapped.

    Returns:
        A wrapped async function that returns the processed image and detailed metadata.
    """
    @functools.wraps(func)
    async def wrapper(
        self: 'ImagePreprocessingProcessor', img: np.ndarray, **kwargs: Any
    ) -> Tuple[np.ndarray, ProcessingStepResult]:
        step_name = func.__name__
        logger = structlog.get_logger(f"{self.name}.{step_name}")
        start_time = time.time()

        # Capture input state
        input_bytes = await asyncio.to_thread(self._cv2_to_bytes, img)
        input_hash = hashlib.md5(input_bytes).hexdigest()

        # Execute the actual processing step
        processed_img = await func(self, img, **kwargs)

        # Capture output state
        output_bytes = await asyncio.to_thread(self._cv2_to_bytes, processed_img)
        output_hash = hashlib.md5(output_bytes).hexdigest()
        
        processing_time_ms = (time.time() - start_time) * 1000

        # Assemble metadata
        metadata = StepMetadata(
            input_hash=input_hash,
            output_hash=output_hash,
            processing_time_ms=processing_time_ms,
            parameters=kwargs
        )

        result = ProcessingStepResult(
            step_name=step_name,
            input_image=base64.b64encode(input_bytes).decode('utf-8'),
            output_image=base64.b64encode(output_bytes).decode('utf-8'),
            metadata=metadata,
        )
        
        logger.info(
            "Sub-step completed",
            duration_ms=f"{processing_time_ms:.2f}",
            input_hash=input_hash,
            output_hash=output_hash
        )

        return processed_img, result
    return wrapper