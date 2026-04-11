"""
Image preprocessing for nutrition label OCR.

Cleans up raw photos of nutrition labels to maximize Tesseract accuracy.
Pipeline: load → grayscale → resize (if low-res) → adaptive threshold → Gaussian blur → return numpy array.
"""

import numpy as np
import cv2
from PIL import Image
from typing import Union
from pathlib import Path


# Minimum width in pixels before we upscale.  A typical nutrition label scanned
# at 300 DPI is ~900-1200 px wide.  Below this threshold the text is likely too
# small for reliable OCR.
_MIN_WIDTH = 800


def preprocess(image: Union[str, Path, Image.Image, np.ndarray]) -> np.ndarray:
    """
    Accept a PIL Image, file path (str/Path), or numpy array and return a
    cleaned grayscale numpy array ready for Tesseract OCR.

    Steps:
        1. Load / convert to OpenCV BGR numpy array
        2. Convert to grayscale
        3. Resize if image width < _MIN_WIDTH (preserves aspect ratio)
        4. Adaptive thresholding (Gaussian, block 11, C=2)
        5. Gaussian blur (3×3) to reduce salt-and-pepper noise

    Returns:
        np.ndarray – single-channel (grayscale) preprocessed image.
    """

    # ------------------------------------------------------------------
    # 3.1.1.1  Accept PIL Image or file path as input
    # ------------------------------------------------------------------
    img = _load_image(image)

    # ------------------------------------------------------------------
    # 3.1.1.2  Convert to grayscale
    # ------------------------------------------------------------------
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ------------------------------------------------------------------
    # 3.1.1.3  Resize if image is too small (< 300 DPI equivalent)
    # ------------------------------------------------------------------
    gray = _resize_if_small(gray)

    # ------------------------------------------------------------------
    # 3.1.1.4  Adaptive thresholding (ADAPTIVE_THRESH_GAUSSIAN_C)
    # ------------------------------------------------------------------
    thresh = cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )

    # ------------------------------------------------------------------
    # 3.1.1.5  Gaussian blur to reduce noise
    # ------------------------------------------------------------------
    blurred = cv2.GaussianBlur(thresh, (3, 3), 0)

    # ------------------------------------------------------------------
    # 3.1.1.6  Return processed image as numpy array
    # ------------------------------------------------------------------
    return blurred


# ======================================================================
# Internal helpers
# ======================================================================

def _load_image(source: Union[str, Path, Image.Image, np.ndarray]) -> np.ndarray:
    """Convert any supported input type to a BGR numpy array."""

    if isinstance(source, np.ndarray):
        # Already a numpy array — assume BGR (OpenCV convention)
        if source.ndim == 2:
            # Grayscale array → convert to 3-channel so downstream cvtColor works uniformly
            return cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
        return source

    if isinstance(source, Image.Image):
        # PIL Image → numpy BGR
        rgb = np.array(source.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # str or Path → read from disk
    path = str(source)
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image at '{path}'")
    return img


def _resize_if_small(gray: np.ndarray) -> np.ndarray:
    """Up-scale the image proportionally if its width is below _MIN_WIDTH."""

    h, w = gray.shape[:2]
    if w < _MIN_WIDTH:
        scale = _MIN_WIDTH / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return gray
