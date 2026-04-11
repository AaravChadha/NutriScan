"""Nutrition label extraction via Groq's vision API.

Replaces the Tesseract OCR + regex pipeline with a single vision LLM call
for the Upload Label and Recipe "Add from Label" flows. The vision model
reads the label photo directly and returns a structured JSON object that
maps cleanly to `NutritionData`.

This path handles poor lighting, off-axis shots, glare, and stylized
labels far better than Tesseract — cases where OCR + regex fundamentally
cannot recover the values. The Tesseract path remains as a fallback for
offline use or when GROQ_API_KEY is unset.
"""

import base64
import json
import os
import re
from dataclasses import dataclass

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from src.llm.prompts import (
    build_label_vision_system_prompt,
    build_label_vision_user_prompt,
)
from src.nutrition.models import NutritionData

load_dotenv()

# Same Groq vision model used by food_identifier. Llama 4 Scout is the
# current free-tier vision model on Groq after the 3.2 vision previews
# were decommissioned.
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


@dataclass
class LabelReadResult:
    """Bundle of what extract_label_with_vision returns."""

    nutrition: NutritionData
    raw_json: str  # for debugging / raw-text expander
    confidence: float  # 0.0-1.0 from the vision model
    fields_parsed: int  # count of nutrient fields > 0


# Fields we ask the vision model to fill in NutritionData.
_NUTRIENT_FIELDS = [
    "calories",
    "total_fat",
    "saturated_fat",
    "trans_fat",
    "cholesterol",
    "sodium",
    "total_carbs",
    "dietary_fiber",
    "total_sugars",
    "added_sugars",
    "protein",
    "vitamin_d",
    "calcium",
    "iron",
    "potassium",
]


def _extract_json(text: str) -> str:
    """Strip markdown code fences from a vision model response.

    Vision preview models on Groq don't support response_format JSON mode,
    so they sometimes wrap the JSON in ```json ... ``` fences.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text


def _coerce_float(value, default: float = 0.0) -> float:
    """Best-effort float coercion from vision model output."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_label_with_vision(image_bytes: bytes) -> LabelReadResult | None:
    """Read a nutrition facts label from image bytes using Groq vision.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG/HEIC — vision API handles
            re-encoding). Pass the result of `uploaded_file.read()` or the
            output of `Image.save(buffer, format='JPEG')`.

    Returns:
        LabelReadResult on success, or None on any failure (no API key,
        network error, invalid JSON, not a label). Surfaces errors via
        `st.error` so the caller can fall back to Tesseract without
        double-reporting.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Caller is responsible for choosing a fallback; don't show an
        # error since this is a legitimate "no vision available" state.
        return None

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    messages = [
        {"role": "system", "content": build_label_vision_system_prompt()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_label_vision_user_prompt()},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=0.1,  # label reading should be deterministic
            max_tokens=2048,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        st.error(f"Vision label reader failed: {e}")
        return None

    json_text = _extract_json(raw)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        st.error("Vision model returned invalid JSON. Falling back to OCR.")
        return None

    if not isinstance(data, dict):
        return None

    confidence = _coerce_float(data.get("confidence"), 0.0)

    nutrition = NutritionData(
        **{field: _coerce_float(data.get(field)) for field in _NUTRIENT_FIELDS},
        serving_size=str(data.get("serving_size") or "").strip(),
        servings_per_container=_coerce_float(
            data.get("servings_per_container"), 1.0
        ),
        ingredients_list=str(data.get("ingredients_list") or "").strip(),
    )

    fields_parsed = sum(
        1 for field in _NUTRIENT_FIELDS if getattr(nutrition, field) > 0
    )

    return LabelReadResult(
        nutrition=nutrition,
        raw_json=json_text,
        confidence=confidence,
        fields_parsed=fields_parsed,
    )
