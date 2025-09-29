import cv2
import numpy as np
from skimage.transform import radon
from typing import List, Tuple, Dict, Any, Optional
import io
from PIL import Image
import time
import hashlib
import base64
import functools
from domain.models import ProcessingStepResult, StepMetadata
import structlog

logger = structlog.get_logger(__name__)

def instrument_step(func):
    """
    Decorator to instrument a preprocessing step, capturing metadata such as
    timing, image hashes, and parameters.
    """
    @functools.wraps(func)
    def wrapper(self, img: np.ndarray, **kwargs) -> Tuple[np.ndarray, ProcessingStepResult]:
        step_name = func.__name__
        start_time = time.time()

        # Capture input state
        input_bytes = self._cv2_to_bytes(img)
        input_hash = hashlib.md5(input_bytes).hexdigest()

        # Execute the actual processing step
        # The 'return_type' is now handled by the decorator's logic
        kwargs.pop('return_type', None) 
        processed_img = func(self, img, **kwargs)

        # Capture output state
        output_bytes = self._cv2_to_bytes(processed_img)
        output_hash = hashlib.md5(output_bytes).hexdigest()
        
        processing_time_ms = (time.time() - start_time) * 1000

        # Assemble metadata
        metadata = StepMetadata(
            input_hash=input_hash,
            output_hash=output_hash,
            processing_time_ms=processing_time_ms,
            parameters=kwargs  # Capture any parameters passed to the step
        )

        result = ProcessingStepResult(
            step_name=step_name,
            input_image=base64.b64encode(input_bytes).decode('utf-8'),
            output_image=base64.b64encode(output_bytes).decode('utf-8'),
            metadata=metadata,
        )
        
        logger.info(
            f"Step '{step_name}' completed in {processing_time_ms:.2f}ms. "
            f"Input: {input_hash}, Output: {output_hash}"
        )

        return processed_img, result
    return wrapper

class ImagePreprocessor:
    """
    A service to preprocess images for OCR and other document intelligence tasks.
    This class follows the Strategy Pattern, where each method is a specific
    preprocessing strategy that can be combined into a pipeline.
    """

    def run_pipeline_on_list(
        self, image_bytes_list: List[bytes], pipeline: Optional[List[str]] = None
    ) -> Tuple[List[bytes], List[List[ProcessingStepResult]]]:
        """
        Runs a configurable preprocessing pipeline on a list of image bytes.

        Args:
            image_bytes_list: A list of images, each as bytes.
            pipeline: A list of strings specifying the preprocessing steps to apply.
                      Defaults to ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"].

        Returns:
            A tuple containing:
            - A list of final processed images, each as bytes.
            - A list of lists of ProcessingStepResult objects, one for each page.
        """
        if pipeline is None:
            pipeline = ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"]

        all_pages_results = []
        final_images = []
        for image_bytes in image_bytes_list:
            processed_image, page_results = self.run_pipeline(image_bytes, pipeline)
            final_images.append(self._cv2_to_bytes(processed_image))
            all_pages_results.append(page_results)
            
        return final_images, all_pages_results

    def run_pipeline(
        self, image_bytes: bytes, pipeline: List[str]
    ) -> Tuple[np.ndarray, List[ProcessingStepResult]]:
        """
        Runs a configurable preprocessing pipeline on a single image.

        Args:
            image_bytes: The input image as bytes.
            pipeline: A list of strings specifying the preprocessing steps.

        Returns:
            A tuple containing:
            - The final processed image as a NumPy array.
            - A list of ProcessingStepResult objects.
        """
        img = self._bytes_to_cv2(image_bytes)
        processing_results = []

        for step in pipeline:
            if hasattr(self, step):
                method = getattr(self, step)
                # The decorator now handles the return type and result creation
                img, result = method(img)
                processing_results.append(result)
            else:
                logger.warning(f"Preprocessing step '{step}' not found. Skipping.")

        return img, processing_results

    def _bytes_to_cv2(self, image_bytes: bytes) -> np.ndarray:
        """Converts image bytes to a cv2 image."""
        image = Image.open(io.BytesIO(image_bytes))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def _cv2_to_bytes(self, img: np.ndarray) -> bytes:
        """Converts a cv2 image back to bytes."""
        is_success, buffer = cv2.imencode(".jpg", img)
        if not is_success:
            raise ValueError("Could not convert processed image back to bytes.")
        return buffer.tobytes()

    @instrument_step
    def deskew(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Deskews an image using the Radon transform.
        This is critical for improving OCR accuracy on scanned documents.
        """
        grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        (h, w) = grayscale.shape
        diagonal = int(np.ceil(np.sqrt(h**2 + w**2)))
        pad_top = (diagonal - h) // 2
        pad_bottom = diagonal - h - pad_top
        pad_left = (diagonal - w) // 2
        pad_right = diagonal - w - pad_left
        
        padded_gray = cv2.copyMakeBorder(grayscale, pad_top, pad_bottom, pad_left, pad_right, 
                                         cv2.BORDER_CONSTANT, value=0)

        I = cv2.Canny(padded_gray, 50, 200, apertureSize=3)

        radius = diagonal // 2
        center = (diagonal // 2, diagonal // 2)
        mask = np.zeros_like(I, dtype=np.uint8)
        cv2.circle(mask, center, radius, 255, -1)

        I = cv2.bitwise_and(I, I, mask=mask)

        theta = np.linspace(-90.0, 90.0, 180, endpoint=False)
        sinogram = radon(I, theta=theta)
        rotation_angle = theta[np.argmax(np.sum(sinogram, axis=0))]

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
        deskewed = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return deskewed

    @instrument_step
    def to_grayscale(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Converts an image to grayscale. Reduces complexity and noise.
        """
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    @instrument_step
    def enhance_contrast(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        This is particularly effective for images with uneven lighting.
        """
        if len(img.shape) > 2 and img.shape[2] > 1:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(img)

    @instrument_step
    def binarize_adaptive(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Applies adaptive thresholding to create a binary image.
        This is a crucial step for isolating text from the background.
        """
        if len(img.shape) > 2 and img.shape[2] > 1:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    @instrument_step
    def denoise(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Applies non-local means denoising to reduce noise while preserving edges.
        Useful for noisy scans.
        """
        return cv2.fastNlMeansDenoising(img, None, 10, 7, 21)