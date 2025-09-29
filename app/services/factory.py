from .pdf_processor import PDFProcessor
from .image_preprocessor import ImagePreprocessor
from .template_service import TemplateService


def get_pdf_processor() -> PDFProcessor:
    return PDFProcessor()

def get_image_preprocessor() -> ImagePreprocessor:
    return ImagePreprocessor()

def get_template_service() -> TemplateService:
    return TemplateService()