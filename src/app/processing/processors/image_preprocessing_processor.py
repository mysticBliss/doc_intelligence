from __future__ import annotations

import asyncio
import base64
import functools
import hashlib
import io
import time
from typing import Any, Callable, Coroutine, Dict, List, Tuple

import cv2
import numpy as np
import structlog
from app.processing.decorators import instrument_step, instrument_sub_step
from app.processing.payloads import (
    DocumentPayload,
    ImagePreprocessingResult,
    ProcessingStepResult,
    ProcessorResult,
    StepMetadata,
)
from app.processing.processors.base import BaseProcessor, ProcessorResult
from PIL import Image
from pydantic import BaseModel


class ImagePreprocessingProcessor(BaseProcessor):
    """Applies a series of preprocessing steps to an image."""

    @property
    def name(self) -> str:
        return "image_preprocessing_processor"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.validate_config()
        self.available_steps = self._get_available_steps()

    def validate_config(self):
        if "steps" not in self.config or not isinstance(self.config["steps"], list):
            raise ValueError("Image Preprocessing 'steps' must be a list.")

    @instrument_step
    async def process(self, payload: DocumentPayload, *, logger: structlog.stdlib.BoundLogger) -> ProcessorResult:
        """
        Processes the document by applying a series of image enhancement steps.
        """
        if not payload.file_content:
            raise ValueError("Image data is required for preprocessing.")

        img = self._bytes_to_cv2(payload.file_content)
        executed_steps: List[ProcessingStepResult] = []

        for step_config in self.config["steps"]:
            step_name = step_config.get("name")
            if not step_name:
                self.logger.warning("Skipping step with no name.", config=step_config)
                continue

            step_func = self.available_steps.get(step_name)
            if not step_func:
                self.logger.warning(f"Step '{step_name}' not found. Skipping.")
                continue

            params = step_config.get("params", {})
            self.logger.info(f"Executing step: {step_name}", params=params)
            
            # The instrumented sub-step now returns the result object directly
            img, step_result = await step_func(img, **params)
            executed_steps.append(step_result)

        final_image_bytes = self._cv2_to_bytes(img)
        result_data = ImagePreprocessingResult(
            final_image=base64.b64encode(final_image_bytes).decode("utf-8"),
            steps=executed_steps,
        )

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            structured_results=result_data.model_dump(),
        )

    def _get_available_steps(self) -> Dict[str, Callable[..., Coroutine[Any, Any, Tuple[np.ndarray, ProcessingStepResult]]]]:
        """
        Returns a dictionary of available image processing steps.
        """
        return {
            "deskew": self.deskew,
            "denoise": self.denoise,
            "to_grayscale": self.to_grayscale,
            "binarize": self.binarize,
            "enhance_contrast": self.enhance_contrast,
            "opening": self.opening,
            "closing": self.closing,
            "canny": self.canny,
            "correct_perspective": self.correct_perspective,
        }

    @staticmethod
    def _bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
        """Converts image bytes to a CV2 image (numpy array)."""
        image = Image.open(io.BytesIO(image_bytes))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _cv2_to_bytes(img: np.ndarray) -> bytes:
        """Converts a CV2 image (numpy array) to bytes."""
        is_success, buffer = cv2.imencode(".png", img)
        if not is_success:
            raise ValueError("Failed to encode image to bytes.")
        return buffer.tobytes()

    async def _create_step_result(
        self,
        step_name: str,
        input_img: np.ndarray,
        output_img: np.ndarray,
        params: Dict[str, Any],
    ) -> ProcessingStepResult:
        """Helper to create a ProcessingStepResult with all metadata."""
        input_bytes = await asyncio.to_thread(self._cv2_to_bytes, input_img)
        output_bytes = await asyncio.to_thread(self._cv2_to_bytes, output_img)

        metadata = StepMetadata(
            input_hash=hashlib.md5(input_bytes).hexdigest(),
            output_hash=hashlib.md5(output_bytes).hexdigest(),
            parameters=params,
        )
        return ProcessingStepResult(
            step_name=step_name,
            status="success",
            input_image=base64.b64encode(input_bytes).decode('utf-8'),
            output_image=base64.b64encode(output_bytes).decode('utf-8'),
            metadata=metadata,
        )

    @instrument_sub_step
    async def deskew(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Corrects skew in the image.
        """
        processed_img = await asyncio.to_thread(self._deskew_sync, img)
        result = await self._create_step_result("deskew", img, processed_img, kwargs)
        return processed_img, result

    def _deskew_sync(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    @instrument_sub_step
    async def denoise(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Removes noise from the image.
        """
        strength = kwargs.get("strength", 10)
        processed_img = await asyncio.to_thread(cv2.fastNlMeansDenoisingColored, img, None, strength, 10, 7, 21)
        result = await self._create_step_result("denoise", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def to_grayscale(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Converts the image to grayscale.
        """
        if len(img.shape) == 3 and img.shape[2] == 3:
            processed_img = await asyncio.to_thread(cv2.cvtColor, img, cv2.COLOR_BGR2GRAY)
        else:
            processed_img = img
        result = await self._create_step_result("to_grayscale", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def binarize(
        self, img: np.ndarray, **kwargs: Any
    ) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Binarizes the image.
        """
        threshold = kwargs.get("threshold", 127)
        adaptive = kwargs.get("adaptive", False)

        grayscale_img = img
        if len(img.shape) > 2 and img.shape[2] != 1:
            grayscale_img, _ = await self.to_grayscale(img)

        if adaptive:
            processed_img = await asyncio.to_thread(
                cv2.adaptiveThreshold,
                grayscale_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        else:
            _, processed_img = await asyncio.to_thread(cv2.threshold, grayscale_img, threshold, 255, cv2.THRESH_BINARY)
        
        result = await self._create_step_result("binarize", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def enhance_contrast(
        self, img: np.ndarray, **kwargs: Any
    ) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Enhances the contrast of the image using CLAHE.
        """
        clip_limit = kwargs.get("clip_limit", 2.0)
        tile_grid_size = kwargs.get("tile_grid_size", 8)

        grayscale_img = img
        if len(img.shape) > 2 and img.shape[2] != 1:
            grayscale_img, _ = await self.to_grayscale(img)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
        processed_img = await asyncio.to_thread(clahe.apply, grayscale_img)
        result = await self._create_step_result("enhance_contrast", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def opening(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Applies morphological opening to the image.
        """
        kernel_size = kwargs.get("kernel_size", 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        processed_img = await asyncio.to_thread(cv2.morphologyEx, img, cv2.MORPH_OPEN, kernel)
        result = await self._create_step_result("opening", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def closing(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Applies morphological closing to the image.
        """
        kernel_size = kwargs.get("kernel_size", 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        processed_img = await asyncio.to_thread(cv2.morphologyEx, img, cv2.MORPH_CLOSE, kernel)
        result = await self._create_step_result("closing", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def canny(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Applies Canny edge detection to the image.
        """
        threshold1 = kwargs.get("threshold1", 100)
        threshold2 = kwargs.get("threshold2", 200)
        processed_img = await asyncio.to_thread(cv2.Canny, img, threshold1, threshold2)
        result = await self._create_step_result("canny", img, processed_img, kwargs)
        return processed_img, result

    @instrument_sub_step
    async def correct_perspective(self, img: np.ndarray, **kwargs: Any) -> Tuple[np.ndarray, ProcessingStepResult]:
        """
        Corrects the perspective of the image.
        """
        processed_img = await asyncio.to_thread(self._correct_perspective_sync, img)
        result = await self._create_step_result("correct_perspective", img, processed_img, kwargs)
        return processed_img, result

    def _correct_perspective_sync(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            if len(approx) == 4:
                screen_cnt = approx
                break
        else:
            self.logger.warning("Could not find a 4-point contour for perspective correction. Returning original image.")
            return img

        # The order of points in the contour is top-left, top-right, bottom-right, bottom-left
        rect = np.zeros((4, 2), dtype="float32")
        s = screen_cnt.sum(axis=2)
        rect[0] = screen_cnt[np.argmin(s)]
        rect[2] = screen_cnt[np.argmax(s)]

        diff = np.diff(screen_cnt, axis=2)
        rect[1] = screen_cnt[np.argmin(diff)]
        rect[3] = screen_cnt[np.argmax(diff)]

        (tl, tr, br, bl) = rect

        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")

        m = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, m, (max_width, max_height))

        return warped