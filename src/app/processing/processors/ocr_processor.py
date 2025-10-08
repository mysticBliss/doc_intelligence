import pytesseract
from PIL import Image
import io
import asyncio
import structlog
import magic
import base64
from typing import Any, Dict, Optional

from app.processing.decorators import instrument_step
from app.processing.processors.base import BaseProcessor
from app.processing.payloads import DocumentPayload, ProcessorResult


class OcrProcessor(BaseProcessor):
    name = "ocr_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.validate_config()

    def validate_config(self):
        """Validates the processor configuration for Tesseract settings."""
        if "language" not in self.config:
            self.config["language"] = "eng"
        if "dpi" not in self.config:
            self.config["dpi"] = 300
        elif not isinstance(self.config["dpi"], int) or self.config["dpi"] <= 0:
            raise ValueError("Configuration 'dpi' must be a positive integer.")

        if "page_segmentation_mode" not in self.config:
            self.config["page_segmentation_mode"] = 3
        elif not isinstance(self.config["page_segmentation_mode"], int) or not (0 <= self.config["page_segmentation_mode"] <= 13):
            raise ValueError("Configuration 'page_segmentation_mode' must be an integer between 0 and 13.")

        if "ocr_engine_mode" not in self.config:
            self.config["ocr_engine_mode"] = 3
        elif not isinstance(self.config["ocr_engine_mode"], int) or not (0 <= self.config["ocr_engine_mode"] <= 3):
            raise ValueError("Configuration 'ocr_engine_mode' must be an integer between 0 and 3.")

    @instrument_step
    async def process(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """Extracts text from an image using Tesseract OCR with configurable parameters."""
        image_bytes = base64.b64decode(payload.file_content)
        mime_type = magic.from_buffer(image_bytes, mime=True)
        if not mime_type.startswith("image"):
            raise ValueError(f"OcrProcessor only accepts image files, but received {mime_type}")

        image = Image.open(io.BytesIO(image_bytes))

        # Get config with defaults
        language = self.config["language"]
        dpi = self.config["dpi"]
        psm = self.config["page_segmentation_mode"]
        oem = self.config["ocr_engine_mode"]

        # Construct the Tesseract configuration string
        tesseract_config = f"--dpi {dpi} --psm {psm} --oem {oem}"

        self.logger.info(
            "ocr.processing.started",
            language=language,
            tesseract_config=tesseract_config,
        )

        extracted_text = await asyncio.to_thread(
            pytesseract.image_to_string, image, lang=language, config=tesseract_config
        )

        # Create a concise summary for logging
        output_summary = (extracted_text[:80] + '...') if len(extracted_text) > 80 else extracted_text

        self.logger.info("ocr.processing.finished", text_length=len(extracted_text))

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            output=output_summary.strip(),
            structured_results={"text": extracted_text},
            metadata={"page_number": payload.page_number},
        )