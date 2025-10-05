import fitz  # PyMuPDF
from PIL import Image
import io
from typing import List, Tuple, Optional
from app.domain.models import PageMetadata

class PDFProcessor:
    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def pdf_to_images(
        self, pdf_bytes: bytes, page_numbers: Optional[List[int]] = None
    ) -> Tuple[List[bytes], List[PageMetadata]]:
        """
        Converts a PDF file in bytes to a list of JPEG image bytes and generates metadata.
        If page_numbers is provided, only those pages are converted.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            image_bytes_list = []
            page_metadata_list = []

            pages_to_process = []
            if page_numbers:
                total_pages = len(doc)
                # Validate page numbers (must be 1-indexed)
                for pn in page_numbers:
                    if not 1 <= pn <= total_pages:
                        raise ValueError(
                            f"Invalid page number: {pn}. Document has {total_pages} pages."
                        )
                pages_to_process = [p - 1 for p in page_numbers]  # Convert to 0-indexed
            else:
                pages_to_process = range(len(doc))

            for page_num in pages_to_process:
                page = doc.load_page(page_num)
                pixmap = page.get_pixmap(dpi=self.dpi)
                img = Image.frombytes(
                    "RGB", [pixmap.width, pixmap.height], pixmap.samples
                )
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="JPEG")
                image_bytes = img_byte_arr.getvalue()
                image_bytes_list.append(image_bytes)

                page_metadata = PageMetadata(
                    page_number=page_num + 1,
                    image_size_bytes=len(image_bytes),
                    image_format="JPEG",
                    image_dimensions=img.size,
                )
                page_metadata_list.append(page_metadata)

            doc.close()
            return image_bytes_list, page_metadata_list
        except Exception as e:
            # In a real enterprise app, you'd have structured logging here
            print(f"An error occurred during PDF processing: {e}")
            raise

    def crop_image(self, image_bytes: bytes, bbox: 'BoundingBox') -> bytes:
        """
        Crops an image based on a bounding box.
        The bounding box coordinates are assumed to be normalized (0.0 to 1.0).
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size

            # Denormalize coordinates
            left = int(bbox.x0 * width)
            top = int(bbox.y0 * height)
            right = int(bbox.x1 * width)
            bottom = int(bbox.y1 * height)

            cropped_img = img.crop((left, top, right, bottom))

            img_byte_arr = io.BytesIO()
            cropped_img.save(img_byte_arr, format="JPEG")
            return img_byte_arr.getvalue()
        except Exception as e:
            print(f"An error occurred during image cropping: {e}")
            raise