from .pdf_processor import PDFProcessor
from .image_preprocessor import ImagePreprocessor
from .template_service import TemplateService
from .image_processing_service import ImageProcessingService


def get_pdf_processor() -> PDFProcessor:
    return PDFProcessor()

def get_image_preprocessor() -> ImagePreprocessor:
    return ImagePreprocessor()

def get_image_processing_service() -> ImageProcessingService:
    return ImageProcessingService()

def get_template_service() -> TemplateService:
    return TemplateService()