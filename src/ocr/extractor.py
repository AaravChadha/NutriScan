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

# Separator between nutrient name and value. Accepts whitespace, colon,
# period, comma, or hyphen — handles real-world artifacts like
# "Iron:0.3mg" (punchout label) or "Sodium, 160mg" (comma after name).
_SEP = r"[\s:.,\-]*"

# Value + optional "less than" prefix. Some labels say "Less than 1g" or
# "<1g" for trace nutrients; capture the digit and ignore the prefix.
# Also allow comma as decimal separator (Tesseract sometimes OCRs "." as ",").
_VAL = r"(?:<|less\s*than\s*)?\s*(\d+[.,]?\d*)"

# Unit suffix for mg/g with tolerance for double-letter OCR artifacts like
# "Mmg" (should be "Mg") — accepts any mix of m/whitespace before the g.
# Trailing g is optional because Tesseract frequently swallows it into the
# next token (e.g. "Protein 20g" → "proteim:209"). Strong nutrient-name
# context keeps false positives low.
_MG = r"[m\s]*g?"
_G = r"\s*g?"

_NUTRIENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- fats ---------------------------------------------------------
    ("trans_fat",      re.compile(rf"trans\s*fat{_SEP}{_VAL}{_G}",  re.IGNORECASE)),
    ("saturated_fat",  re.compile(rf"saturated\s*fat{_SEP}{_VAL}{_G}",  re.IGNORECASE)),
    ("total_fat",      re.compile(rf"total\s*fat{_SEP}{_VAL}{_G}",  re.IGNORECASE)),

    # --- cholesterol & sodium -----------------------------------------
    ("cholesterol",    re.compile(rf"cholesterol{_SEP}{_VAL}\s*{_MG}", re.IGNORECASE)),
    ("sodium",         re.compile(rf"sodium{_SEP}{_VAL}\s*{_MG}",     re.IGNORECASE)),

    # --- carbohydrates ------------------------------------------------
    ("dietary_fiber",  re.compile(rf"dietary\s*fiber{_SEP}{_VAL}{_G}",    re.IGNORECASE)),
    ("total_sugars",   re.compile(rf"total\s*sugars?{_SEP}{_VAL}{_G}",    re.IGNORECASE)),
    # Added sugars has two real-world orderings:
    #   Classic: "Incl. Added Sugars 10g" / "Added Sugars 10g"
    #   Modern FDA (2016+): "Includes 0g Added Sugars" — value BEFORE words
    # OCR also often mangles "Includes" (e.g. "incldes") so match `incl\w*`.
    ("added_sugars",   re.compile(
        rf"incl\w*\s*{_VAL}\s*g?\s*added\s*sugars?"
        rf"|(?:incl\.?\s*|added\s*)sugars?{_SEP}{_VAL}{_G}",
        re.IGNORECASE,
    )),
    # "Total Carbohydrate" gets OCRed as "Carbohvdrate", "Carbohydnte",
    # etc. Match "carb" followed by up to 15 lowercase letters, then value.
    ("total_carbs",    re.compile(rf"total\s*carb[a-z]{{0,15}}{_SEP}{_VAL}{_G}",    re.IGNORECASE)),

    # --- protein ------------------------------------------------------
    # Tesseract sometimes misreads "Protein" as "Proteim" / "Protien" / etc.
    ("protein",        re.compile(rf"prote[a-z]{{1,4}}{_SEP}{_VAL}{_G}",      re.IGNORECASE)),

    # --- calories -----------------------------------------------------
    ("calories",       re.compile(rf"calories{_SEP}{_VAL}",         re.IGNORECASE)),

    # --- micronutrients -----------------------------------------------
    ("vitamin_d",      re.compile(rf"vitamin\s*d{_SEP}{_VAL}\s*(?:mcg|µg|ug)", re.IGNORECASE)),
    ("calcium",        re.compile(rf"calcium{_SEP}{_VAL}\s*{_MG}",    re.IGNORECASE)),
    # Tesseract often misreads "Iron" as "lron" (lowercase L) or "1ron" — accept all three.
    ("iron",           re.compile(rf"[il1]ron{_SEP}{_VAL}\s*{_MG}",    re.IGNORECASE)),
    ("potassium",      re.compile(rf"potassium{_SEP}{_VAL}\s*{_MG}",  re.IGNORECASE)),
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

def _clean_ocr_text(text: str) -> str:
    """
    Heuristic fixups for common Tesseract artifacts on nutrition labels.

    These target high-frequency OCR failures observed on real iPhone photos:
    - Letter stuck to value: "Fatlg" → "Fat 1g", "Fatog" → "Fat 0g"
      (Tesseract eats the space and reads "1" as "l" or "0" as "o" when
      they're adjacent to letters.)
    - Comma used as decimal point: "7,09g" → "7.09g" (handled in _VAL).
    - Leading "S" instead of "5": "S20mg" → "520mg" only if immediately
      followed by 2+ digits (to avoid mangling real words).
    """
    # "<letter>lg" / "<letter>Ig" / "<letter>og" → "<letter> 1g" / " 0g"
    # Only triggers after a letter so we don't corrupt real words. We use
    # lookahead for the "g" / "mg" so the \w-boundary issue goes away —
    # "Fatlgsece" correctly becomes "Fat 1gsece" which then matches the
    # total_fat regex via its value capture + tolerant trailing g.
    text = re.sub(r"([A-Za-z])[lI](?=g)", r"\1 1", text)
    text = re.sub(r"([A-Za-z])[oO](?=g)", r"\1 0", text)

    # "S<digit><digit>mg" / "S<digit><digit>g" — leading 5 misread as S.
    # Require at least 2 trailing digits so we don't mangle "Smg" or "Sugar".
    text = re.sub(r"\bS(\d{2,})(\s*m?g\b)", r"5\1\2", text)

    return text


def _parse_nutrition(text: str) -> tuple[NutritionData, int]:
    """
    Apply regex patterns to OCR text and return a populated NutritionData
    plus the count of fields that were successfully extracted.
    """

    # Clean up common OCR artifacts before running the regex patterns.
    text = _clean_ocr_text(text)

    parsed: dict[str, float] = {}

    # --- 3.1.2.3  Nutrient regex matching ---
    # Some patterns use alternation (e.g. added_sugars has two formats),
    # which produces multiple capture groups where only one is populated
    # per match. Pick the first non-None group.
    for field_name, pattern in _NUTRIENT_PATTERNS:
        match = pattern.search(text)
        if match:
            value_str = next((g for g in match.groups() if g is not None), None)
            if value_str is not None:
                try:
                    # Replace comma-decimal ("7,09") with period before parsing
                    parsed[field_name] = float(value_str.replace(",", "."))
                except ValueError:
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
