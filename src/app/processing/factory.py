from typing import Dict, Type

from app.core.config import settings
from app.core.logging import LoggerRegistry
from app.processing.processors.base import BaseProcessor
from app.processing.processors.document_classifier_processor import DocumentClassifierProcessor
from app.processing.processors.image_preprocessing_processor import ImagePreprocessingProcessor
from app.processing.processors.ocr_processor import OcrProcessor
from app.processing.processors.pdf_image_extraction_processor import PDFImageExtractionProcessor
from app.processing.processors.vlm_processor import VlmProcessor
from app.processing.processors.enhanced_pdf_processor import EnhancedPdfProcessor
from app.processing.processors.sentiment_analyzer_processor import SentimentAnalyzerProcessor


class ProcessorFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProcessorFactory, cls).__new__(cls)
            cls._instance._processor_registry: Dict[str, Type[BaseProcessor]] = {
                "image_preprocessor": ImagePreprocessingProcessor,
                "ocr_processor": OcrProcessor,
                "pdf_extraction_processor": PDFImageExtractionProcessor,
                "vlm_processor": VlmProcessor,
                "enhanced_pdf_processor": EnhancedPdfProcessor,
                "document_classifier_processor": DocumentClassifierProcessor,
                "sentiment_analyzer": SentimentAnalyzerProcessor,
            }
        return cls._instance

    def create_processor(self, processor_name: str, config: Dict) -> BaseProcessor:
        """
        Factory method to create a single processor instance.

        Args:
            processor_name: The name of the processor to create.
            config: The configuration for the processor.

        Returns:
            An instantiated processor object.

        Raises:
            ValueError: If the requested processor is not in the registry.
        """
        processor_class = self._processor_registry.get(processor_name)
        if not processor_class:
            raise ValueError(
                f"Unknown processor: '{processor_name}'. "
                f"Available processors: {list(self._processor_registry.keys())}"
            )

        logger = LoggerRegistry.get_processor_logger(processor_name)

        if processor_name == "enhanced_pdf_processor":
            return processor_class(config=config, factory=self, logger=logger)

        if processor_name == "vlm_processor":
            return processor_class(config=config, ollama_base_url=settings.OLLAMA_API_BASE_URL, logger=logger)

        return processor_class(config=config, logger=logger)