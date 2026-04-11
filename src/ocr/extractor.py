"""
OCR extraction for nutrition labels.

Runs Tesseract on a preprocessed image and parses the raw text into a
structured NutritionData object using regex patterns.
"""

import re
from dataclasses import dataclass
from typing import Union

import numpy as np
import pytesseract
from PIL import Image
from pathlib import Path

from src.ocr.preprocessor import preprocess
from src.nutrition.models import NutritionData


# Total number of numeric nutrient fields we attempt to parse.
_TOTAL_NUTRIENT_FIELDS = 15


@dataclass
class ExtractionResult:
    """Bundles the parsed NutritionData with debugging helpers."""

    nutrition: NutritionData
    raw_text: str
    fields_parsed: int
    confidence: str  # "high" | "medium" | "low"


# ======================================================================
# 3.1.2.3  Regex patterns for each nutrient field
# ======================================================================
# Each pattern is a tuple of (NutritionData field name, compiled regex).
# Patterns are intentionally forgiving:
#   • optional whitespace between words and between value and unit
#   • value may be integer or decimal
#   • unit is captured but only used for context (mg vs g)
#
# Order matters for fields like "total fat" vs plain "fat" — more specific
# patterns come first to avoid mis-matches.

_NUTRIENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- fats ---------------------------------------------------------
    ("trans_fat",      re.compile(r"trans\s*fat\s*(\d+\.?\d*)\s*g",  re.IGNORECASE)),
    ("saturated_fat",  re.compile(r"saturated\s*fat\s*(\d+\.?\d*)\s*g",  re.IGNORECASE)),
    ("total_fat",      re.compile(r"total\s*fat\s*(\d+\.?\d*)\s*g",  re.IGNORECASE)),

    # --- cholesterol & sodium -----------------------------------------
    ("cholesterol",    re.compile(r"cholesterol\s*(\d+\.?\d*)\s*m?g", re.IGNORECASE)),
    ("sodium",         re.compile(r"sodium\s*(\d+\.?\d*)\s*m?g",     re.IGNORECASE)),

    # --- carbohydrates ------------------------------------------------
    ("dietary_fiber",  re.compile(r"dietary\s*fiber\s*(\d+\.?\d*)\s*g",    re.IGNORECASE)),
    ("total_sugars",   re.compile(r"total\s*sugars?\s*(\d+\.?\d*)\s*g",    re.IGNORECASE)),
    ("added_sugars",   re.compile(r"(?:incl\.?\s*|added\s*)sugars?\s*(\d+\.?\d*)\s*g", re.IGNORECASE)),
    ("total_carbs",    re.compile(r"total\s*carb(?:ohydrate)?s?\s*(\d+\.?\d*)\s*g",    re.IGNORECASE)),

    # --- protein ------------------------------------------------------
    ("protein",        re.compile(r"protein\s*(\d+\.?\d*)\s*g",      re.IGNORECASE)),

    # --- calories -----------------------------------------------------
    ("calories",       re.compile(r"calories\s*(\d+\.?\d*)",         re.IGNORECASE)),

    # --- micronutrients -----------------------------------------------
    ("vitamin_d",      re.compile(r"vitamin\s*d\s*(\d+\.?\d*)\s*(?:mcg|µg|ug)", re.IGNORECASE)),
    ("calcium",        re.compile(r"calcium\s*(\d+\.?\d*)\s*m?g",    re.IGNORECASE)),
    # Tesseract often misreads "Iron" as "lron" (lowercase L) or "1ron" — accept all three.
    ("iron",           re.compile(r"[il1]ron\s*(\d+\.?\d*)\s*m?g",    re.IGNORECASE)),
    ("potassium",      re.compile(r"potassium\s*(\d+\.?\d*)\s*m?g",  re.IGNORECASE)),
]

# Serving size & servings per container
_SERVING_SIZE_RE = re.compile(
    r"serving\s*size\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
# Servings per container — match either ordering:
#   "Servings Per Container 8"  /  "Servings Per Container: about 8"
#   "8 servings per container"  (FDA 2014+ label puts the number first)
_SERVINGS_PER_CONTAINER_RE = re.compile(
    r"servings?\s*per\s*container\s*[:\-]?\s*(?:about\s*)?(\d+\.?\d*)",
    re.IGNORECASE,
)
_SERVINGS_PER_CONTAINER_REVERSED_RE = re.compile(
    r"(?:about\s*)?(\d+\.?\d*)\s*servings?\s*per\s*container",
    re.IGNORECASE,
)


# ======================================================================
# Public API
# ======================================================================

def extract(image: Union[str, Path, Image.Image, np.ndarray]) -> ExtractionResult:
    """
    End-to-end: preprocess image → run Tesseract → parse into NutritionData.

    Parameters:
        image: anything accepted by ``preprocessor.preprocess()``

    Returns:
        ExtractionResult with parsed nutrition, raw OCR text, count of
        successfully parsed fields, and a confidence label.
    """

    # ------------------------------------------------------------------
    # 3.1.2.1  Call preprocessor.preprocess(image)
    # ------------------------------------------------------------------
    processed = preprocess(image)

    # ------------------------------------------------------------------
    # 3.1.2.2  Run pytesseract.image_to_string() with config --psm 6
    # ------------------------------------------------------------------
    raw_text: str = pytesseract.image_to_string(processed, config="--psm 6")

    # ------------------------------------------------------------------
    # 3.1.2.3 + 3.1.2.4 + 3.1.2.5  Parse into NutritionData
    # ------------------------------------------------------------------
    nutrition, fields_parsed = _parse_nutrition(raw_text)

    # ------------------------------------------------------------------
    # 3.1.2.6  Confidence indicator
    # ------------------------------------------------------------------
    confidence = _compute_confidence(fields_parsed)

    return ExtractionResult(
        nutrition=nutrition,
        raw_text=raw_text,
        fields_parsed=fields_parsed,
        confidence=confidence,
    )


# ======================================================================
# Internal helpers
# ======================================================================

def _parse_nutrition(text: str) -> tuple[NutritionData, int]:
    """
    Apply regex patterns to OCR text and return a populated NutritionData
    plus the count of fields that were successfully extracted.
    """

    parsed: dict[str, float] = {}

    # --- 3.1.2.3  Nutrient regex matching ---
    for field_name, pattern in _NUTRIENT_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                parsed[field_name] = float(match.group(1))
            except (ValueError, IndexError):
                pass

    fields_parsed = len(parsed)

    # --- Serving info (not counted toward field score) ---
    serving_size = ""
    ssize_match = _SERVING_SIZE_RE.search(text)
    if ssize_match:
        # Clean up: take first line only, strip trailing junk
        serving_size = ssize_match.group(1).strip().split("\n")[0].strip()

    servings_per_container = 1.0
    spc_match = (
        _SERVINGS_PER_CONTAINER_RE.search(text)
        or _SERVINGS_PER_CONTAINER_REVERSED_RE.search(text)
    )
    if spc_match:
        try:
            servings_per_container = float(spc_match.group(1))
        except ValueError:
            pass

    # --- 3.1.2.4  Parse ingredients list ---
    ingredients_list = _parse_ingredients(text)

    # --- 3.1.2.5  Build and return NutritionData ---
    nutrition = NutritionData(
        calories=parsed.get("calories", 0.0),
        total_fat=parsed.get("total_fat", 0.0),
        saturated_fat=parsed.get("saturated_fat", 0.0),
        trans_fat=parsed.get("trans_fat", 0.0),
        cholesterol=parsed.get("cholesterol", 0.0),
        sodium=parsed.get("sodium", 0.0),
        total_carbs=parsed.get("total_carbs", 0.0),
        dietary_fiber=parsed.get("dietary_fiber", 0.0),
        total_sugars=parsed.get("total_sugars", 0.0),
        added_sugars=parsed.get("added_sugars", 0.0),
        protein=parsed.get("protein", 0.0),
        vitamin_d=parsed.get("vitamin_d", 0.0),
        calcium=parsed.get("calcium", 0.0),
        iron=parsed.get("iron", 0.0),
        potassium=parsed.get("potassium", 0.0),
        serving_size=serving_size,
        servings_per_container=servings_per_container,
        ingredients_list=ingredients_list,
    )

    return nutrition, fields_parsed


def _parse_ingredients(text: str) -> str:
    """
    3.1.2.4  Find the "Ingredients:" line and capture everything until the
    next obvious section header (e.g. "Allergen", "Contains", "Distributed",
    "Manufactured", or an all-caps header) or end of text.
    """

    # Find "Ingredients:" (case-insensitive)
    ing_match = re.search(
        r"ingredients\s*[:;]\s*",
        text,
        re.IGNORECASE,
    )
    if not ing_match:
        return ""

    # Grab everything after "Ingredients:"
    remainder = text[ing_match.end():]

    # Cut off at the next section-like header.
    # The keyword alternatives are case-insensitive via the inline (?i:...) flag,
    # but the [A-Z]{5,} "all-caps header" check stays case-sensitive — otherwise
    # IGNORECASE would make it match any 5+ letter word and truncate mid-list.
    end_match = re.search(
        r"\n\s*(?:(?i:allergen|contains|distributed|manufactured|warnings?|storage|"
        r"best\s*(?:by|before)|expir|nutrition\s*facts|percent\s*daily)|"
        r"[A-Z]{5,})",
        remainder,
    )
    if end_match:
        remainder = remainder[: end_match.start()]

    # Clean up: collapse whitespace, strip trailing period/comma
    ingredients = " ".join(remainder.split()).strip().rstrip(".,;")
    return ingredients


def _compute_confidence(fields_parsed: int) -> str:
    """
    3.1.2.6  Simple confidence indicator based on how many of the ~15
    nutrient fields were successfully extracted.
    """
    if fields_parsed >= 10:
        return "high"
    elif fields_parsed >= 5:
        return "medium"
    else:
        return "low"
