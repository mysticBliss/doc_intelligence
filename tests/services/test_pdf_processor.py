import pytest
from app.services.pdf_processor import PDFProcessor
import fitz  # PyMuPDF

# Create a dummy PDF in memory for testing
@pytest.fixture
def dummy_pdf_bytes() -> bytes:
    doc = fitz.open()  # New empty PDF
    page = doc.new_page()
    page.insert_text((50, 72), "Hello, world!")
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def test_pdf_to_images_success(dummy_pdf_bytes):
    """Test that a valid PDF is converted into a list of image bytes."""
    processor = PDFProcessor()
    image_bytes_list, _ = processor.pdf_to_images(dummy_pdf_bytes)
    assert isinstance(image_bytes_list, list)
    assert len(image_bytes_list) == 1
    assert isinstance(image_bytes_list[0], bytes)
    # A simple check to see if it looks like a JPEG
    assert image_bytes_list[0].startswith(b'\xff\xd8')

def test_pdf_to_images_invalid_bytes():
    """Test that the processor handles invalid PDF bytes gracefully."""
    processor = PDFProcessor()
    with pytest.raises(Exception):  # fitz raises a generic exception
        processor.pdf_to_images(b"this is not a pdf")