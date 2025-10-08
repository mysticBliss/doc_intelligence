from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from pdf2image.exceptions import PDFPageCountError
import base64
import io
import uuid
from typing import List, Any, Dict, Set
import structlog

from app.processing.decorators import instrument_step
from app.processing.processors.base import BaseProcessor
from app.processing.payloads import DocumentPayload, ProcessorResult


class PDFImageExtractionProcessor(BaseProcessor):
    name = "pdf_extraction_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.validate_config()

    def _parse_page_range(self, page_range_str: str, max_pages: int) -> Set[int]:
        """Parses a page range string (e.g., '1,3-5,10') into a set of page numbers."""
        if not page_range_str:
            return set(range(1, max_pages + 1))

        pages = set()
        parts = page_range_str.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    if start > end or start < 1 or end > max_pages:
                        raise ValueError(f"Invalid page range: {part}. Pages must be within 1-{max_pages}.")
                    pages.update(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"Invalid page range format: '{part}'. Use numbers or 'start-end'.")
            else:
                try:
                    page = int(part)
                    if page < 1 or page > max_pages:
                        raise ValueError(f"Invalid page number: {page}. Page must be within 1-{max_pages}.")
                    pages.add(page)
                except ValueError:
                    raise ValueError(f"Invalid page number format: '{part}'. Must be a number.")
        return pages

    def validate_config(self):
        """Validates the processor configuration."""
        if "resolution" not in self.config:
            self.config["resolution"] = 300
        elif not isinstance(self.config["resolution"], int) or self.config["resolution"] <= 0:
            raise ValueError("Configuration 'resolution' must be a positive integer.")
        
        supported_formats = ["PNG", "JPEG", "TIFF"]
        if "image_format" not in self.config:
            self.config["image_format"] = "PNG"
        elif self.config["image_format"].upper() not in supported_formats:
            raise ValueError(f"Configuration 'image_format' must be one of {supported_formats}.")

    @instrument_step
    async def process(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """Extracts images from a PDF, creating a new DocumentPayload for each page with lineage."""
        if not payload.file_content:
            self.logger.error("No file content found in payload for PDF extraction.")
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error_message="Input payload must contain file_content for PDF processing."
            )
        
        try:
            pdf_bytes = payload.file_content
        except Exception as e:
            self.logger.error("pdf_extraction.base64_decode_failed", error=str(e))
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error_message=f"Failed to decode base64 content from image_data: {e}"
            )

        resolution = self.config.get("resolution", 300)
        image_format = self.config.get("image_format", "PNG").upper()
        page_range_str = self.config.get("page_range")

        try:
            info = pdfinfo_from_bytes(pdf_bytes)
            max_pages = info["Pages"]
        except PDFPageCountError as e:
            self.logger.error("pdf_extraction.failed", error="Could not determine page count.")
            return ProcessorResult(processor_name=self.name, status="failure", error_message="Invalid PDF: could not read page count.")

        try:
            target_pages = self._parse_page_range(page_range_str, max_pages)
        except ValueError as e:
            self.logger.error("pdf_extraction.config_error", error=str(e))
            return ProcessorResult(processor_name=self.name, status="failure", error_message=str(e))

        if not target_pages:
            self.logger.info("pdf_extraction.skipped", reason="Page range is empty.")
            return ProcessorResult(processor_name=self.name, status="success", output="No pages selected for extraction.", structured_results={"document_payloads": []})

        parent_doc_id = str(uuid.uuid4())
        child_payloads = []

        # Convert all pages in the required range at once for efficiency
        all_images = convert_from_bytes(
            pdf_bytes,
            dpi=resolution,
            fmt=image_format.lower(),
            thread_count=4  # Use multiple threads for faster conversion
        )

        page_map = {i + 1: img for i, img in enumerate(all_images)}

        for page_num in sorted(list(target_pages)):
            if page_num in page_map:
                img_byte_arr = io.BytesIO()
                page_map[page_num].save(img_byte_arr, format=image_format)
                encoded_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

                new_payload = DocumentPayload(
                    job_id=payload.job_id,
                    file_name=f"{payload.file_name}_page_{page_num}.{image_format.lower()}",
                    file_content=encoded_image,
                    parent_document_id=parent_doc_id,
                    page_number=page_num,
                    results=[]
                )
                child_payloads.append(new_payload)

        output_summary = f"Extracted {len(child_payloads)} pages from PDF."
        self.logger.info("pdf_extraction.success", num_pages_extracted=len(child_payloads), parent_document_id=parent_doc_id)

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            output=output_summary,
            structured_results={"document_payloads": child_payloads},
        )