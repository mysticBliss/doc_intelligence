import base64
import hashlib
import time
import asyncio
from typing import Any, Dict, List, TYPE_CHECKING

import structlog

from app.processing.decorators import instrument_step, instrument_sub_step
from app.processing.payloads import DocumentPayload
from app.processing.processors.base import BaseProcessor, ProcessorResult

if TYPE_CHECKING:
    from app.processing.factory import ProcessorFactory


class EnhancedPdfProcessor(BaseProcessor):
    """
    Orchestrates a complex PDF processing workflow, acting as a sub-pipeline.
    """

    name = "enhanced_pdf_processor"

    def __init__(self, config: Dict[str, Any], factory: "ProcessorFactory", logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.factory = factory
        self.validate_config()

    def validate_config(self):
        """Validates the processor-specific configuration."""
        self.image_extractor = self.factory.create_processor("pdf_extraction_processor", self.config.get("pdf_extraction_processor", {}))
        self.preprocessor = self.factory.create_processor("image_preprocessor", self.config.get("image_preprocessor", {}))
        self.ocr_processor = self.factory.create_processor("ocr_processor", self.config.get("ocr_processor", {}))
        self.vlm_processor = self.factory.create_processor("vlm_processor", self.config.get("vlm_processor", {}))

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """
        Executes the enhanced PDF processing pipeline.
        """
        document_id = hashlib.md5(base64.b64decode(payload.image_data)).hexdigest()
        self.logger = self.logger.bind(document_id=document_id)

        # 1. Extract images from PDF
        extraction_result = await self.image_extractor.process(payload)
        if not extraction_result.success:
            return extraction_result
        extracted_images_b64 = extraction_result.result_data.get("images", [])

        # 2. Preprocess all images
        processed_images_b64 = await self._preprocess_images(extracted_images_b64)

        # 3. Run OCR and VLM on each preprocessed image
        page_analysis_results = await self._analyze_images(processed_images_b64, document_id)

        # 4. Aggregate results
        aggregated_results = []
        for i, page_results in enumerate(page_analysis_results):
            ocr_res, vlm_res = page_results
            aggregated_results.append(
                {
                    "page_number": i + 1,
                    "ocr_result": ocr_res.result_data if ocr_res.success else ocr_res.error,
                    "vlm_result": vlm_res.result_data if vlm_res.success else vlm_res.error,
                }
            )

        return ProcessorResult(
            processor_name=self.name,
            success=True,
            result_data={"pages": aggregated_results},
        )

    async def _preprocess_images(self, images_b64: List[str]) -> List[str]:
        """Preprocesses a list of images concurrently."""
        preprocessing_tasks = []
        for img_b64 in images_b64:
            image_payload = DocumentPayload(image_data=img_b64)
            preprocessing_tasks.append(self.preprocessor.process(image_payload))

        processed_results = await asyncio.gather(*preprocessing_tasks)
        return [res.result_data["image_data"] for res in processed_results if res.success]

    async def _analyze_images(self, images_b64: List[str], document_id: str) -> List[Any]:
        """Runs OCR and VLM analysis on a list of images concurrently."""
        analysis_tasks = []
        for i, img_b64 in enumerate(images_b64):
            image_id = f"{document_id}-{i + 1}"
            image_log = self.logger.bind(image_id=image_id)
            image_payload = DocumentPayload(image_data=img_b64)

            # We need to pass the child logger to the sub-processors.
            # The context is not automatically propagated across process boundaries
            # or to manually called processor instances.
            # A deeper refactoring could implement context propagation if needed.
            task_ocr = self.ocr_processor.process(image_payload)
            task_vlm = self.vlm_processor.process(image_payload)

            analysis_tasks.append(
                self._run_and_log_page_analysis(asyncio.gather(task_ocr, task_vlm), image_log)
            )

        return await asyncio.gather(*analysis_tasks)

    async def _run_and_log_page_analysis(self, analysis_task: asyncio.Task, image_log: Any) -> Any:
        """Helper to log start/finish for a single page's analysis."""
        # The logger is passed here to ensure the image_id is bound for this specific sub-task.
        image_log.info("page_analysis.start")
        result = await analysis_task
        image_log.info("page_analysis.finished")
        return result