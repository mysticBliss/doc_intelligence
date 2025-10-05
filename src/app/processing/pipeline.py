import asyncio
import time
from typing import Any, Coroutine, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field, model_validator

from app.core.schemas.base import BaseProcessorConfig
from app.processing.factory import ProcessorFactory
from app.processing.processors.base import BaseProcessor, ProcessorResult
from app.processing.payloads import DocumentPayload


class Step(BaseModel):
    """Defines a single step in a DAG-based pipeline."""

    processor: str
    dependencies: List[str] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """
    Validated pipeline configuration supporting both linear and DAG execution.
    """

    name: str
    description: str
    execution_mode: str
    pipeline: Union[List[Dict[str, Any]], Dict[str, Any]]
    max_concurrency: int = Field(5, gt=0)


class ProcessingPipeline:
    """
    Orchestrates the execution of a processing pipeline based on a dynamic configuration.
    Supports both simple linear execution and complex DAG-based workflows.
    """

    def __init__(self, config: Dict[str, Any], factory: ProcessorFactory):
        """
        Initializes the pipeline with a validated configuration and a processor factory.

        Args:
            config: The raw pipeline configuration dictionary.
            factory: An instance of ProcessorFactory to create processor instances.
        """
        self.config = PipelineConfig.model_validate(config)
        self.factory = factory
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def run(self, payload: DocumentPayload, logger: Optional[structlog.stdlib.BoundLogger] = None) -> List[ProcessorResult]:
        """
        Executes the pipeline based on the validated configuration.

        Args:
            **kwargs: Initial arguments for the pipeline.

        Returns:
            A list of ProcessorResult objects from all processors.
        """
        log = logger or self.logger
        log = log.bind(pipeline_id=str(time.time()))
        log.info("pipeline.start", config=self.config.model_dump())
        start_time = time.perf_counter()

        if self.config.execution_mode == "simple":
            results = await self._run_linear(log, payload)
        elif self.config.execution_mode == "dag":
            results = await self._run_dag(log, payload)
        else:
            # This case should be prevented by Pydantic validation
            raise ValueError(f"Invalid execution_mode: {self.config.execution_mode}")

        duration_ms = round((time.perf_counter() - start_time) * 1000)
        log.info("pipeline.finished", duration_ms=duration_ms)
        return results

    async def _run_linear(
        self, logger: structlog.stdlib.BoundLogger, payload: DocumentPayload
    ) -> List[ProcessorResult]:
        """Executes a simple linear pipeline."""
        pipeline_results: List[ProcessorResult] = []
        current_payloads = [payload]

        for i, p_config in enumerate(self.config.pipeline):
            processor = self.factory.create_processor(p_config["name"], p_config.get("params", {}))
            next_payloads = []
            has_next_payloads = False

            for p_idx, current_payload in enumerate(current_payloads):
                result = await self._execute_step(logger, f"{i}_{p_idx}", processor, {"payload": current_payload, **p_config.get("params", {})})
                pipeline_results.append(result)

                if result.status != "success":
                    logger.error("pipeline.linear.failed", step=i, processor_name=processor.name)
                    # Stop processing this branch of the pipeline
                    continue

                # Handle different types of results to create the next set of payloads
                if result.results:
                    initial_len = len(next_payloads)
                    if isinstance(result.results, list) and all(isinstance(item, DocumentPayload) for item in result.results):
                        next_payloads.extend(result.results)
                    elif isinstance(result.results, dict) and 'images' in result.results and isinstance(result.results['images'], list):
                        for img_b64 in result.results['images']:
                            next_payloads.append(DocumentPayload(image_data=img_b64))
                    elif isinstance(result.results, dict):
                        try:
                            next_payloads.append(DocumentPayload(**result.results))
                        except Exception:
                            logger.warning("Could not create DocumentPayload from result dict", step=i, result=result.results)
                    else:
                        logger.warning("Unhandled result type", step=i, result_type=type(result.results))
                    if len(next_payloads) > initial_len:
                        has_next_payloads = True

            current_payloads = next_payloads
            if not current_payloads:
                if has_next_payloads:
                    logger.info("Pipeline terminated: last step produced results but no subsequent steps are defined.", step=i)
                else:
                    logger.info("Pipeline branch terminated due to no further payloads.", step=i)
                break

        return pipeline_results

    async def _run_dag(self, logger: Any, payload: DocumentPayload) -> List[ProcessorResult]:
        """Executes a DAG-based pipeline with parallel execution for independent steps."""
        step_results: Dict[str, List[ProcessorResult]] = {}
        execution_levels = self._get_dag_execution_order()

        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        nodes_by_id = {node['id']: node for node in self.config.pipeline['nodes']}

        for level, steps_in_level in enumerate(execution_levels):
            tasks: List[Coroutine] = []
            task_step_map: List[Dict[str, Any]] = []

            for step_name in steps_in_level:
                step_config = nodes_by_id[step_name]
                processor = self.factory.create_processor(step_config["processor"], step_config.get("params", {}))

                dependency_payloads: List[DocumentPayload] = []
                dependencies_failed = False

                if not step_config.get("dependencies"):
                    # This is a root node, use the initial payload
                    dependency_payloads.append(payload)
                else:
                    # This is a subsequent node, gather payloads from dependencies
                    for dep_name in step_config.get("dependencies", []):
                        dep_results_list = step_results.get(dep_name)
                        if not dep_results_list:
                            logger.error("pipeline.dag.dependency_missing", step=step_name, dependency=dep_name)
                            dependencies_failed = True
                            break

                        for dep_result in dep_results_list:
                            if dep_result.status != "success":
                                logger.warning("pipeline.dag.dependency_failed", step=step_name, dependency=dep_name)
                                dependencies_failed = True
                                break
                            
                            if isinstance(dep_result.results, dict) and 'images' in dep_result.results:
                                for img_b64 in dep_result.results['images']:
                                    dependency_payloads.append(DocumentPayload(image_data=img_b64))
                            elif isinstance(dep_result.results, list) and all(isinstance(r, DocumentPayload) for r in dep_result.results):
                                dependency_payloads.extend(dep_result.results)
                            elif isinstance(dep_result.results, dict):
                                try:
                                    dependency_payloads.append(DocumentPayload(**dep_result.results))
                                except Exception:
                                    logger.warning("Could not create DocumentPayload from dependency result dict", step=step_name, dep_result=dep_result.results)

                        if dependencies_failed:
                            break
                
                if dependencies_failed:
                    step_results[step_name] = [ProcessorResult(
                        processor_name=processor.name,
                        status="skipped",
                        error_message=f"Skipped due to failed dependencies."
                    )]
                    continue

                if not dependency_payloads:
                    logger.warning("pipeline.dag.no_payloads_for_step", step=step_name)
                    continue

                # Execute the step for each payload
                for i, payload_obj in enumerate(dependency_payloads):
                    step_args = {"payload": payload_obj, **step_config.get("params", {})}
                    task = self._execute_step(logger, f"{step_name}_{i}", processor, step_args, semaphore)
                    tasks.append(task)
                    task_step_map.append({"name": step_name, "processor": processor.name})

            if not tasks:
                continue

            level_results = await asyncio.gather(*tasks)

            for result, step_info in zip(level_results, task_step_map):
                step_name = step_info["name"]
                if step_name not in step_results:
                    step_results[step_name] = []
                step_results[step_name].append(result)

        # Aggregate results for the final output
        final_results: List[ProcessorResult] = []
        for step_name, results_list in step_results.items():
            if not results_list:
                continue

            if len(results_list) == 1:
                final_results.append(results_list[0])
            else:
                # Aggregate multiple results for a single step (fan-in)
                aggregated_results_content = []
                final_status = "success"
                error_messages = []
                
                for res in results_list:
                    if res.status != "success":
                        final_status = "failure"
                        if res.error_message:
                            error_messages.append(res.error_message)
                    if res.results:
                        aggregated_results_content.append(res.results)
                
                # Create a single representative result for the step
                final_results.append(ProcessorResult(
                    processor_name=results_list[0].processor_name,
                    status=final_status,
                    results={"aggregated_results": aggregated_results_content},
                    error_message=" | ".join(error_messages) if error_messages else None
                ))
                
        return final_results

    async def _execute_step(
        self,
        logger: structlog.stdlib.BoundLogger,
        step_id: Union[int, str],
        processor: BaseProcessor,
        args: Dict[str, Any],
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> ProcessorResult:
        """Executes a single processor step, acquiring a semaphore if provided, and handles exceptions."""
        async def process_func() -> ProcessorResult:
            logger.info(
                "pipeline.step.start",
                step=step_id,
                processor_name=processor.name,
            )
            try:
                result = await processor.process(**args)
                return result
            except Exception as e:
                logger.error(
                    "pipeline.step.exception",
                    step=step_id,
                    processor_name=processor.name,
                    error=str(e),
                    exc_info=True,
                )
                return ProcessorResult(
                    processor_name=processor.name,
                    status="failure",
                    error_message=f"An unexpected error occurred: {str(e)}",
                )

        if semaphore:
            async with semaphore:
                return await process_func()
        else:
            return await process_func()

    def _get_dag_execution_order(self) -> List[List[str]]:
        """
        Performs a topological sort to determine the execution order of DAG steps.
        Groups steps that can be executed in parallel.
        Raises a ValueError if a cycle is detected.
        """
        if not isinstance(self.config.pipeline, dict) or "nodes" not in self.config.pipeline:
            return []

        graph = {node["id"]: set(node.get("dependencies", [])) for node in self.config.pipeline["nodes"]}
        execution_levels = []

        while True:
            ready = {name for name, deps in graph.items() if not deps}

            if not ready:
                break

            execution_levels.append(sorted(list(ready)))  # Sort for deterministic order

            for name in ready:
                del graph[name]

            for deps in graph.values():
                deps.difference_update(ready)

        if graph:
            raise ValueError(f"A cycle was detected in the DAG involving steps: {list(graph.keys())}")

        return execution_levels