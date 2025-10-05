import pytesseract
from PIL import Image
import io
import asyncio
import structlog
import magic
import base64
from typing import Any, Dict

from app.processing.decorators import instrument_step
from app.processing.processors.base import BaseProcessor, ProcessorResult
from app.processing.payloads import DocumentPayload


class OcrProcessor(BaseProcessor):
    name = "ocr_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.validate_config()

    def validate_config(self):
        """Validates the processor configuration for Tesseract settings."""
        if "dpi" in self.config:
            if not isinstance(self.config["dpi"], int) or self.config["dpi"] <= 0:
                raise ValueError("Configuration 'dpi' must be a positive integer.")

        if "page_segmentation_mode" in self.config:
            psm = self.config["page_segmentation_mode"]
            if not isinstance(psm, int) or not (0 <= psm <= 13):
                raise ValueError("Configuration 'page_segmentation_mode' must be an integer between 0 and 13.")

        if "ocr_engine_mode" in self.config:
            oem = self.config["ocr_engine_mode"]
            if not isinstance(oem, int) or not (0 <= oem <= 3):
                raise ValueError("Configuration 'ocr_engine_mode' must be an integer between 0 and 3.")

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """Extracts text from an image using Tesseract OCR with configurable parameters."""
        image_bytes = base64.b64decode(payload.image_data)
        mime_type = magic.from_buffer(image_bytes, mime=True)
        if not mime_type.startswith("image"):
            raise ValueError(f"OcrProcessor only accepts image files, but received {mime_type}")

        image = Image.open(io.BytesIO(image_bytes))

        # Get config with defaults
        language = self.config.get("language", "eng")
        dpi = self.config.get("dpi", 300)
        psm = self.config.get("page_segmentation_mode", 3)
        oem = self.config.get("ocr_engine_mode", 3)

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

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            results={"text": extracted_text},
        )