import asyncio
import base64
import functools
import hashlib
import time
from typing import Any, Callable, Coroutine, Tuple

import numpy as np
import structlog

from app.core.logging import LoggerRegistry
from app.processing.payloads import (
    ProcessingStepResult,
    ProcessorResult,
    StepMetadata,
)
from app.processing.processors.base import BaseProcessor


def instrument_step(
    func: Callable[..., Coroutine[Any, Any, ProcessorResult]]
) -> Callable[..., Coroutine[Any, Any, ProcessorResult]]:
    """
    A decorator for instrumenting a processor's `process` method.

    This decorator standardizes cross-cutting concerns for all processors:
    - Injects page_number and parent_document_id into the result metadata.
    - Measures and logs the execution time of the step.
    - Catches and logs any exceptions, wrapping them in a standardized
      `ProcessorResult` for graceful failure handling.
    """

    @functools.wraps(func)
    async def wrapper(self: BaseProcessor, *args, **kwargs: Any) -> ProcessorResult:
        log = kwargs.get('logger', LoggerRegistry.get_processor_logger(self.name)).bind(processor_name=self.name)
        kwargs['logger'] = log
        log.info(f"{self.name}.start")
        start_time = time.perf_counter()

        # Prepare metadata from the processor's context
        metadata = {
            "page_number": self.page_number,
            "parent_document_id": self.parent_document_id,
        }

        try:
            # Execute the actual processor logic
            result = await func(self, *args, **kwargs)

            if not isinstance(result, ProcessorResult):
                raise TypeError(
                    f"Processor '{self.name}' did not return a ProcessorResult instance."
                )

            duration_ms = round((time.perf_counter() - start_time) * 1000)
            
            # Merge the context metadata into the result
            result.metadata.update(metadata)
            result.metadata["_execution_time_ms"] = duration_ms

            log.info(
                f"{self.name}.finished",
                duration_ms=duration_ms,
                status=result.status,
                **result.metadata,
            )

            return result

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000)
            log.error(
                f"{self.name}.failed",
                error=str(e),
                exc_info=True,
                duration_ms=duration_ms,
                **metadata,
            )

            # Create a failure result with the context metadata
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error_message=f"An unexpected error occurred in {self.name}: {str(e)}",
                metadata=metadata,
            )

    return wrapper


def instrument_sub_step(
    func: Callable[..., Coroutine[Any, Any, Tuple[np.ndarray, ProcessingStepResult]]]
) -> Callable[..., Coroutine[Any, Any, Tuple[np.ndarray, ProcessingStepResult]]]:
    """
    Decorator to instrument an image processing sub-step, capturing metadata
    such as timing. The wrapped function is expected to handle its own
    metadata generation and return a ProcessingStepResult.

    Args:
        func: The async sub-step function to be wrapped.

    Returns:
        A wrapped async function that returns the processed image and detailed metadata.
    """
    @functools.wraps(func)
    async def wrapper(
        self: 'BaseProcessor', img: np.ndarray, **kwargs: Any
    ) -> Tuple[np.ndarray, ProcessingStepResult]:
        step_name = func.__name__
        logger = LoggerRegistry.get_decorator_logger(self.name, step_name)
        start_time = time.time()

        # The wrapped function is now responsible for all processing and result creation.
        processed_img, result = await func(self, img, **kwargs)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # The decorator's only job is to time and log.
        logger.info(
            "Sub-step completed",
            duration_ms=f"{processing_time_ms:.2f}",
            step_name=result.step_name,
            status=result.status,
        )

        # Augment the result with the accurate timing from the decorator
        if result.metadata:
            result.metadata.processing_time_ms = processing_time_ms

        return processed_img, result
    return wrapper