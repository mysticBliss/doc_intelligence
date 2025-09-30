import cv2
import numpy as np
from skimage.transform import radon
from typing import List, Tuple, Dict, Any, Optional
import io
from PIL import Image
import time
import hashlib
import base64
import asyncio
import functools
from app.domain.models import ProcessingStepResult, StepMetadata
import structlog

logger = structlog.get_logger(__name__)

def instrument_step(func):
    """
    Decorator to instrument a preprocessing step, capturing metadata such as
    timing, image hashes, and parameters.
    """
    @functools.wraps(func)
    async def wrapper(self, img: np.ndarray, **kwargs) -> Tuple[np.ndarray, ProcessingStepResult]:
        step_name = func.__name__
        start_time = time.time()

        # Capture input state
        input_bytes = await asyncio.to_thread(self._cv2_to_bytes, img)
        input_hash = hashlib.md5(input_bytes).hexdigest()

        # Execute the actual processing step
        kwargs.pop('return_type', None)
        processed_img = await func(self, img, **kwargs)

        # Capture output state
        output_bytes = await asyncio.to_thread(self._cv2_to_bytes, processed_img)
        output_hash = hashlib.md5(output_bytes).hexdigest()
        
        processing_time_ms = (time.time() - start_time) * 1000

        # Assemble metadata
        metadata = StepMetadata(
            input_hash=input_hash,
            output_hash=output_hash,
            processing_time_ms=processing_time_ms,
            parameters=kwargs
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

    async def run_pipeline_on_list(
        self, image_bytes_list: List[bytes], pipeline: Optional[List[str]] = None
    ) -> Tuple[List[bytes], List[List[ProcessingStepResult]]]:
        """
        Runs a configurable preprocessing pipeline on a list of image bytes.
        """
        if pipeline is None:
            pipeline = ["deskew", "to_grayscale", "enhance_contrast", "binarize_adaptive"]

        tasks = [self.run_pipeline(image_bytes, pipeline) for image_bytes in image_bytes_list]
        results = await asyncio.gather(*tasks)
        
        final_images = [await asyncio.to_thread(self._cv2_to_bytes, res[0]) for res in results]
        all_pages_results = [res[1] for res in results]
            
        return final_images, all_pages_results

    async def run_pipeline(
        self, image_bytes: bytes, pipeline: List[str]
    ) -> Tuple[np.ndarray, List[ProcessingStepResult]]:
        """
        Runs a configurable preprocessing pipeline on a single image.
        """
        img = await asyncio.to_thread(self._bytes_to_cv2, image_bytes)
        processing_results = []

        for step in pipeline:
            if hasattr(self, step):
                method = getattr(self, step)
                img, result = await method(img)
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
    async def deskew(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Deskews an image using the Radon transform.
        """
        return await asyncio.to_thread(self._deskew_sync, img, **kwargs)

    def _deskew_sync(self, img: np.ndarray, **kwargs) -> np.ndarray:
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
    async def to_grayscale(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Converts an image to grayscale. Reduces complexity and noise.
        """
        return await asyncio.to_thread(cv2.cvtColor, img, cv2.COLOR_BGR2GRAY)

    @instrument_step
    async def enhance_contrast(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        """
        return await asyncio.to_thread(self._enhance_contrast_sync, img, **kwargs)

    def _enhance_contrast_sync(self, img: np.ndarray, **kwargs) -> np.ndarray:
        if len(img.shape) > 2 and img.shape[2] > 1:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(img)

    @instrument_step
    async def binarize_adaptive(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Applies adaptive thresholding to create a binary image.
        """
        return await asyncio.to_thread(self._binarize_adaptive_sync, img, **kwargs)

    def _binarize_adaptive_sync(self, img: np.ndarray, **kwargs) -> np.ndarray:
        if len(img.shape) > 2 and img.shape[2] > 1:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    @instrument_step
    async def denoise(self, img: np.ndarray, **kwargs) -> np.ndarray:
        """
        Applies non-local means denoising to reduce noise while preserving edges.
        """
        return await asyncio.to_thread(cv2.fastNlMeansDenoising, img, None, 10, 7, 21)