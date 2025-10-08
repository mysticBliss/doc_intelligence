import asyncio
import time
import uuid
from typing import Any, Coroutine, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field, model_validator

from app.core.schemas.base import BaseProcessorConfig
from app.api.v1.schemas.schemas import DocumentProcessingResult, JobStatus
from app.core.logging import LoggerRegistry
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
        self.logger = LoggerRegistry.get_pipeline_logger()

    async def run(self, payload: DocumentPayload, logger: Optional[structlog.stdlib.BoundLogger] = None) -> DocumentProcessingResult:
        """
        Executes the pipeline and returns a structured, document-centric result.
        """
        log = logger or self.logger
        # Use the payload's document_id if it exists, otherwise generate one.
        # This ensures the root document has a stable ID.
        if not payload.document_id:
            payload.document_id = f"doc_{uuid.uuid4()}"
        log = log.bind(pipeline_id=str(time.time()), document_id=payload.document_id)

        log.info("pipeline.start", config=self.config.model_dump())
        start_time = time.perf_counter()

        final_result = DocumentProcessingResult(
            job_id=payload.job_id,
            status=JobStatus.IN_PROGRESS,
            results=[],
            final_output=None
        )

        try:
            if self.config.execution_mode == "simple":
                all_step_results = await self._run_linear(log, payload)
            elif self.config.execution_mode == "dag":
                all_step_results = await self._run_dag(log, payload)
            else:
                raise ValueError(f"Invalid execution_mode: {self.config.execution_mode}")

            final_result.results = [r.model_dump() for r in all_step_results]
            final_result.final_output = self._aggregate_results(log, all_step_results, payload.document_id)
            final_result.status = JobStatus.SUCCESS

        except Exception as e:
            log.error("pipeline.run.failed", error=str(e), exc_info=True)
            final_result.status = JobStatus.FAILURE
            final_result.error_message = f"Pipeline execution failed: {str(e)}"

        duration_ms = round((time.perf_counter() - start_time) * 1000)
        log.info("pipeline.finished", duration_ms=duration_ms, final_status=final_result.status.value)

        return final_result

    def _aggregate_results(
        self,
        logger: structlog.stdlib.BoundLogger,
        all_results: List[ProcessorResult],
        parent_document_id: str,
    ) -> Dict[str, Any]:
        """
        Aggregates a flat list of ProcessorResult objects into a structured,
        document-centric dictionary, grouping results by page.
        """
        logger.info("pipeline.aggregate.start", result_count=len(all_results))

        # The final output structure
        aggregated_output = {
            "document_id": parent_document_id,
            "status": "success",  # Assume success unless a failure result is found
            "pages": [],
            "document_level_results": {}
        }
        pages_map: Dict[int, Dict[str, Any]] = {}

        for result in all_results:
            # Check for the special orchestrator failure message
            if result.processor_name == "pipeline_orchestrator" and result.status == "failure":
                aggregated_output["status"] = "failure"
                aggregated_output["error_message"] = result.error_message
                # Continue processing other results, but the final status is now failure

            if result.status != "success":
                continue  # Skip failed steps in aggregation

            page_num = result.metadata.get("page_number")
            processor_name = result.processor_name.replace("_processor", "") # Clean name for key

            if page_num is not None:
                # This result belongs to a specific page
                if page_num not in pages_map:
                    pages_map[page_num] = {"page_number": page_num}
                
                # Add the structured result to the page, keyed by processor name
                if result.structured_results:
                    pages_map[page_num][f"{processor_name}_result"] = result.structured_results
            else:
                # This is a document-level result (e.g., the PDF extractor's summary)
                if result.structured_results:
                     aggregated_output["document_level_results"][f"{processor_name}_result"] = result.structured_results


        # Convert the map of pages to a sorted list
        sorted_pages = sorted(pages_map.values(), key=lambda p: p["page_number"])
        aggregated_output["pages"] = sorted_pages

        logger.info("pipeline.aggregate.finished", page_count=len(sorted_pages))
        return aggregated_output

    async def _run_linear(
        self, logger: structlog.stdlib.BoundLogger, initial_payload: DocumentPayload
    ) -> List[ProcessorResult]:
        """Executes a linear pipeline, supporting fan-out for page-based processing."""
        # Payloads are stored in a dictionary keyed by a unique identifier (e.g., page number)
        # For single documents, the key can be a default value like 0.
        payloads_to_process: Dict[Union[int, str], DocumentPayload] = {0: initial_payload}
        all_results: List[ProcessorResult] = []
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        for i, p_config in enumerate(self.config.pipeline):
            processor = self.factory.create_processor(p_config["name"], p_config.get("params", {}))
            logger.info("pipeline.step.start", step=i, processor=processor.name, input_payload_count=len(payloads_to_process))

            tasks = []
            for payload_key, payload in payloads_to_process.items():
                # The key helps correlate results back to the specific payload (page)
                tasks.append(self._execute_step(logger, f"{i}_{payload_key}", processor, payload, semaphore))

            step_results: List[ProcessorResult] = await asyncio.gather(*tasks)
            all_results.extend(step_results)

            next_payloads: Dict[Union[int, str], DocumentPayload] = {}
            fan_out_detected = False

            for result in step_results:
                if result.status != "success":
                    logger.warning("pipeline.step.failed", processor=result.processor_name, error=result.error_message)
                    continue  # This branch of processing stops

                # Check for the fan-out contract
                if (
                    result.structured_results
                    and isinstance(result.structured_results.get("document_payloads"), list)
                ):
                    fan_out_detected = True
                    # A processor (like PDF extractor) has fanned out.
                    # The subsequent steps will run on these new payloads.
                    for new_payload in result.structured_results["document_payloads"]:
                        # The key is now the page number, ensuring unique processing paths.
                        if new_payload.page_number is not None:
                            next_payloads[new_payload.page_number] = new_payload
                        else:
                            # Fallback for non-paginated fan-out
                            next_payloads[str(uuid.uuid4())] = new_payload
                    break  # Exit the loop, as we are now in a new processing context

            if fan_out_detected:
                payloads_to_process = next_payloads
            elif i + 1 < len(self.config.pipeline):
                # For non-fan-out steps, we expect a 1:1 mapping between input payloads and results.
                # The result of the current step becomes the input for the next.
                if len(step_results) == len(payloads_to_process):
                    # Create new payloads from the results of the current step
                    payloads_to_process = {
                        key: DocumentPayload(
                            image_data=res.structured_results.get("image_data") if res.structured_results else None,
                            parent_document_id=payloads_to_process[key].parent_document_id,
                            page_number=res.metadata.get("page_number"),
                            results=payloads_to_process[key].results + [res.dict()]
                        )
                        for (key, res) in zip(payloads_to_process.keys(), step_results)
                        if res.status == "success" and (res.structured_results and res.structured_results.get("image_data"))
                    }
                else:
                    logger.warning("pipeline.step.mismatch", reason="Mismatch between payload and result count in linear flow.", expected=len(payloads_to_process), got=len(step_results))
                    payloads_to_process = {}

            if not payloads_to_process:
                logger.info("pipeline.terminated", reason="No further payloads to process.", last_step=i)
                break

        return all_results

    async def _execute_step(
        self, logger: structlog.stdlib.BoundLogger, step_id: str, processor: BaseProcessor, payload: DocumentPayload, semaphore: asyncio.Semaphore
    ) -> ProcessorResult:
        """Wrapper to execute a single processor step, with semaphore for concurrency control."""
        async with semaphore:
            logger.info("step.execute.start", step_id=step_id, processor=processor.name)
            try:
                # Pass the logger to the process method if the processor accepts it
                result = await processor.execute(payload, logger=logger)
                logger.info(
                    "step.execute.success",
                    step_id=step_id,
                    processor=processor.name,
                    status=result.status,
                    # Log the high-level structure of the result, avoiding large data blobs
                    result_summary={
                        "has_structured_results": bool(result.structured_results),
                        "has_image_data": "image_data" in (result.structured_results or {}),
                        "has_payloads": "document_payloads" in (result.structured_results or {}),
                    },
                )
                return result
            except Exception as e:
                logger.error("step.execute.unhandled_exception", step_id=step_id, processor=processor.name, error=str(e), exc_info=True)
                return ProcessorResult(
                    processor_name=processor.name,
                    status="failure",
                    error_message=f"Unhandled exception in {processor.name}: {str(e)}"
                )


    async def _run_dag(self, logger: Any, payload: DocumentPayload) -> List[ProcessorResult]:
        """Executes a DAG-based pipeline with parallel execution for independent steps."""
        step_results: Dict[str, List[ProcessorResult]] = {}
        execution_levels = self._get_dag_execution_order()

        if not execution_levels:
            self.logger.warning("DAG execution order is empty. No steps will be executed.")
            return []

        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        
        pipeline_nodes = self.config.pipeline.get('nodes', [])
        if not isinstance(pipeline_nodes, list):
            self.logger.error("Invalid pipeline format: 'nodes' must be a list.", pipeline_config=self.config.pipeline)
            return []

        nodes_by_id = {node['id']: node for node in pipeline_nodes}
        payloads_by_step: Dict[str, List[DocumentPayload]] = {"_initial_": [payload]}
        
        executed_steps = set()

        for level, steps_in_level in enumerate(execution_levels):
            tasks: List[Coroutine] = []
            task_to_context_map: List[tuple[str, DocumentPayload]] = []

            for step_id in steps_in_level:
                step_config = nodes_by_id.get(step_id)
                if not step_config:
                    self.logger.error("Configuration for step not found in 'nodes'.", step_id=step_id)
                    continue

                executed_steps.add(step_id)

                # Determine input payloads for this step
                input_payloads: List[DocumentPayload] = []
                dependencies = step_config.get("dependencies", [])
                if not dependencies:
                    # Root node, uses the initial payload
                    input_payloads = payloads_by_step["_initial_"]
                else:
                    # Collect payloads from all parent steps
                    for dep_id in dependencies:
                        if dep_id in payloads_by_step:
                            input_payloads.extend(payloads_by_step[dep_id])

                if not input_payloads:
                    self.logger.warning("No input payloads for step. Skipping.", step_id=step_id)
                    continue
                
                processor = self.factory.create_processor(step_config["processor"], step_config.get("params", {}))

                # Create a task for each payload
                for i, p in enumerate(input_payloads):
                    task_id = f"{step_id}_{i}"
                    tasks.append(self._execute_step(logger, task_id, processor, p, semaphore))
                    task_to_context_map.append((step_id, p))

            if not tasks:
                continue

            level_results = await asyncio.gather(*tasks)

            # Process results and prepare payloads for the next level
            for result, (step_id, original_payload) in zip(level_results, task_to_context_map):
                if step_id not in step_results:
                    step_results[step_id] = []
                step_results[step_id].append(result)

                if result.status != "success":
                    logger.warning("DAG step failed.", processor=result.processor_name, error=result.error_message)
                    continue

                # Initialize the list for the current step if it doesn't exist
                if step_id not in payloads_by_step:
                    payloads_by_step[step_id] = []

                # Check for fan-out (e.g., PDF extractor)
                if result.structured_results and isinstance(result.structured_results.get("document_payloads"), list):
                    payloads_by_step[step_id].extend(result.structured_results["document_payloads"])
                # Check for single image output (e.g., image preprocessor)
                elif result.structured_results and result.structured_results.get("image_data"):
                    # Create a new payload for the next step, ensuring context is carried over
                    new_payload = DocumentPayload(
                        image_data=result.structured_results.get("image_data"),
                        # Explicitly carry over page context from the original payload
                        parent_document_id=original_payload.parent_document_id,
                        page_number=original_payload.page_number,
                        # Append the current result to the history from the original payload
                        results=original_payload.results + [result.dict()]
                    )
                    payloads_by_step[step_id].append(new_payload)
        
        all_results: List[ProcessorResult] = []
        for step_id in executed_steps:
            if step_id in step_results:
                all_results.extend(step_results[step_id])

        logger.info("DAG final validation", 
                    executed_steps=list(executed_steps), 
                    all_nodes=list(nodes_by_id.keys()))

        # Final validation
        if len(executed_steps) != len(nodes_by_id):
            logger.error("Pipeline did not complete successfully. Some steps were not executed.",
                         executed_steps=list(executed_steps), total_steps=len(nodes_by_id))
            # Create a final failure result to ensure the pipeline status is correctly reported
            failure_result = ProcessorResult(
                processor_name="pipeline_orchestrator",
                status="failure",
                error_message="DAG execution incomplete: Not all nodes were executed.",
                metadata={"executed_steps": list(executed_steps), "total_steps": len(nodes_by_id)}
            )
            all_results.append(failure_result)

        return all_results

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