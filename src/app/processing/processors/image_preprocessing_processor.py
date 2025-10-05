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
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        """
        Processes the document by applying a series of image enhancement steps.
        """
        if not payload.image_data:
            raise ValueError("Image data is required for preprocessing.")

        img = self._bytes_to_cv2(payload.image_data)
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
            img = await step_func(img, **params)
            # The decorator will handle the result logging
            # For now, we don't have a detailed step result object here,
            # this would require a bigger refactor of the decorator
            executed_steps.append(ProcessingStepResult(step_name=step_name, status="success", metadata=StepMetadata(parameters=params)))


        final_image_bytes = self._cv2_to_bytes(img)
        result_data = ImagePreprocessingResult(
            final_image=base64.b64encode(final_image_bytes).decode("utf-8"),
            steps=executed_steps,
        )

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            results=result_data.model_dump(),
            image_data=final_image_bytes,
        )

    def _get_available_steps(self) -> Dict[str, Callable[..., Coroutine[Any, Any, np.ndarray]]]:
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

    @instrument_sub_step
    async def deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Corrects skew in the image.
        """
        return await asyncio.to_thread(self._deskew_sync, img)

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
    async def denoise(self, img: np.ndarray, strength: int = 10) -> np.ndarray:
        """
        Removes noise from the image.
        """
        return await asyncio.to_thread(cv2.fastNlMeansDenoisingColored, img, None, strength, 10, 7, 21)


    @instrument_sub_step
    async def to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """
        Converts the image to grayscale.
        """
        if len(img.shape) == 3 and img.shape[2] == 3:
             return await asyncio.to_thread(cv2.cvtColor, img, cv2.COLOR_BGR2GRAY)
        return img


    @instrument_sub_step
    async def binarize(
        self, img: np.ndarray, threshold: int = 127, adaptive: bool = False
    ) -> np.ndarray:
        """
        Binarizes the image.
        """
        if len(img.shape) > 2 and img.shape[2] != 1:
            img = await self.to_grayscale(img)

        if adaptive:
            return await asyncio.to_thread(
                cv2.adaptiveThreshold,
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        else:
            _, binary_img = await asyncio.to_thread(cv2.threshold, img, threshold, 255, cv2.THRESH_BINARY)
            return binary_img

    @instrument_sub_step
    async def enhance_contrast(
        self, img: np.ndarray, clip_limit: float = 2.0, tile_grid_size: int = 8
    ) -> np.ndarray:
        """
        Enhances the contrast of the image using CLAHE.
        """
        if len(img.shape) > 2 and img.shape[2] != 1:
            img = await self.to_grayscale(img)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
        return await asyncio.to_thread(clahe.apply, img)

    @instrument_sub_step
    async def opening(self, img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """
        Applies morphological opening to the image.
        """
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return await asyncio.to_thread(cv2.morphologyEx, img, cv2.MORPH_OPEN, kernel)

    @instrument_sub_step
    async def closing(self, img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """
        Applies morphological closing to the image.
        """
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return await asyncio.to_thread(cv2.morphologyEx, img, cv2.MORPH_CLOSE, kernel)

    @instrument_sub_step
    async def canny(self, img: np.ndarray, threshold1: int = 100, threshold2: int = 200) -> np.ndarray:
        """
        Applies Canny edge detection to the image.
        """
        return await asyncio.to_thread(cv2.Canny, img, threshold1, threshold2)

    @instrument_sub_step
    async def correct_perspective(self, img: np.ndarray) -> np.ndarray:
        """
        Corrects the perspective of the image.
        """
        return await asyncio.to_thread(self._correct_perspective_sync, img)

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