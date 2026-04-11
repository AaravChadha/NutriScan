"""
Image preprocessing for nutrition label OCR.

Cleans up raw photos of nutrition labels to maximize Tesseract accuracy.

Pipeline: load (honoring EXIF) → grayscale → resize to target range →
denoise → adaptive threshold → return numpy array.

The target-size step is critical for iPhone / Android photos. They're
typically 3000-4000 px wide; feeding that directly into adaptive threshold
with a small block size produces noise, because each block only covers a
fraction of a text glyph. We downsample large images into a 1200-1600 px
band where Tesseract's default PSM works well, and upscale small images
up to 800 px so low-res scans aren't starved of pixels.
"""

import numpy as np
import cv2
from PIL import Image, ImageOps
from typing import Union
from pathlib import Path

# Register HEIC/HEIF opener with PIL so iPhone photos uploaded directly
# from the camera roll (e.g. via st.file_uploader) can be opened without
# a prior format conversion. No-op at runtime if Pillow already supports
# the format or if pillow-heif isn't installed.
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass


# Normalize everything to a single target width. Upscale tiny scans with
# INTER_CUBIC (adds detail), downsample big phone photos with INTER_AREA
# (best for shrinking, avoids moiré). Chosen empirically: 1600 px is wide
# enough to keep text legible on FDA-style clean scans (14/15 fields on
# tests/sample_labels/fda_2014.jpg) AND normalizes 3000-4000 px iPhone
# photos down to a size where the fixed-size adaptive threshold actually
# lines up with character heights.
_TARGET_WIDTH = 1600

# Adaptive threshold block size — must be odd. Tuned for the target width:
# too small and text strokes become noise, too large and shadows bleed
# into glyphs. Block 25 / C=2 was the best sweep result for FDA 2014.
_ADAPTIVE_BLOCK_SIZE = 25
_ADAPTIVE_C = 2


def preprocess(image: Union[str, Path, Image.Image, np.ndarray]) -> np.ndarray:
    """
    Accept a PIL Image, file path (str/Path), or numpy array and return a
    cleaned grayscale numpy array ready for Tesseract OCR.

    Steps:
        1. Load / convert to OpenCV BGR numpy array (honoring EXIF rotation)
        2. Convert to grayscale
        3. Resize to _TARGET_WIDTH (upscales small scans, downsamples photos)
        4. Adaptive thresholding (Gaussian, block 25, C=2)
        5. Gaussian blur to reduce salt-and-pepper noise post-threshold

    Returns:
        np.ndarray – single-channel (binarized) preprocessed image.
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
    # 3.1.1.3  Normalize image width → _TARGET_WIDTH
    # ------------------------------------------------------------------
    gray = _normalize_width(gray)

    # ------------------------------------------------------------------
    # 3.1.1.4  Adaptive thresholding (ADAPTIVE_THRESH_GAUSSIAN_C)
    # ------------------------------------------------------------------
    thresh = cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=_ADAPTIVE_BLOCK_SIZE,
        C=_ADAPTIVE_C,
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
    """Convert any supported input type to a BGR numpy array.

    For PIL Images and file paths we honor EXIF orientation tags via
    ImageOps.exif_transpose — iPhone / Android photos are almost always
    stored landscape-on-disk with a rotation tag, and feeding an unrotated
    sideways image to Tesseract produces garbage OCR (Phase 4.2 bug).
    """

    if isinstance(source, np.ndarray):
        # Already a numpy array — assume BGR (OpenCV convention)
        if source.ndim == 2:
            # Grayscale array → convert to 3-channel so downstream cvtColor works uniformly
            return cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
        return source

    if isinstance(source, Image.Image):
        pil_img = ImageOps.exif_transpose(source)
        rgb = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # str or Path → read via PIL so we can honor EXIF orientation, then
    # convert to BGR for OpenCV. (cv2.imread ignores EXIF tags entirely.)
    path = str(source)
    try:
        pil_img = Image.open(path)
    except (FileNotFoundError, Image.UnidentifiedImageError) as e:
        raise FileNotFoundError(f"Could not read image at '{path}'") from e
    pil_img = ImageOps.exif_transpose(pil_img)
    rgb = np.array(pil_img.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _normalize_width(gray: np.ndarray) -> np.ndarray:
    """Scale the image so width = _TARGET_WIDTH, preserving aspect ratio.

    Uses INTER_CUBIC when upscaling (adds detail) and INTER_AREA when
    downsampling (best for shrinking, avoids moiré).
    """
    h, w = gray.shape[:2]
    if w == _TARGET_WIDTH:
        return gray

    scale = _TARGET_WIDTH / w
    interp = cv2.INTER_AREA if w > _TARGET_WIDTH else cv2.INTER_CUBIC
    return cv2.resize(
        gray, (_TARGET_WIDTH, int(h * scale)), interpolation=interp
    )
