"""Food identification from photos using Groq's vision API.

Given raw image bytes (JPEG/PNG), calls a Groq vision model to identify
each food/beverage item and estimate its portion in grams. Used by the
Snap Food tab (`src/ui/pages_snap.py`).
"""

import base64
import io
import json
import os
import re

import streamlit as st
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass
from dotenv import load_dotenv
from groq import Groq

from src.llm.prompts import build_vision_system_prompt, build_vision_user_prompt
from src.nutrition.models import NutritionData
from src.nutrition.usda_client import lookup_food

load_dotenv()

# Groq's vision-capable model. The original plan used
# llama-3.2-90b-vision-preview, but Groq decommissioned all Llama 3.2
# vision preview models. Llama 4 Scout is the current free-tier vision
# model on Groq. If this is deprecated, check
# https://console.groq.com/docs/deprecations for the replacement.
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _extract_json(text: str) -> str:
    """Strip markdown code fences from a model response so json.loads works.

    Vision preview models on Groq don't support response_format JSON mode,
    so they sometimes wrap the JSON in ```json ... ``` fences.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    # Otherwise try to find the outermost JSON object
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text


def identify_food(image_bytes: bytes) -> list[dict]:
    """Identify food items in an image using Groq vision.

    Args:
        image_bytes: Raw image bytes (JPEG or PNG).

    Returns:
        List of dicts, each with keys `name` (str), `estimated_grams` (float),
        `confidence` (float in 0..1). Returns `[]` on any failure (network
        error, bad JSON, empty response) — also calls `st.error` so the user
        sees what went wrong.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not set in environment.")
        return []

    # Encode image as base64 data URL. Groq's vision API accepts JPEG/PNG.
    # Detect format and re-encode HEIC/HEIF/unknown formats to JPEG.
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime = "image/png"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        mime = "image/webp"
    elif image_bytes[:3] in (b'\xff\xd8\xff',):
        mime = "image/jpeg"
    else:
        buf = io.BytesIO(image_bytes)
        img = Image.open(buf).convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        image_bytes = out.getvalue()
        mime = "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    messages = [
        {"role": "system", "content": build_vision_system_prompt()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_vision_user_prompt()},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        st.error(f"Food identification failed: {e}")
        return []

    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        st.error("The AI returned an invalid response. Please try another photo.")
        return []

    foods = data.get("foods", [])
    if not isinstance(foods, list):
        return []

    # Coerce/validate each item so downstream code can trust the schema.
    cleaned = []
    for item in foods:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            grams = float(item.get("estimated_grams", 0))
        except (TypeError, ValueError):
            grams = 0.0
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        cleaned.append(
            {
                "name": name,
                "estimated_grams": max(0.0, grams),
                "confidence": max(0.0, min(1.0, confidence)),
            }
        )
    return cleaned


# ── USDA Bridge ─────────────────────────────────────────────────────────────

# USDA nutrient IDs → NutritionData field names. Values in foodNutrients are
# per 100g for Foundation/SR Legacy/FNDDS and are computed per 100g from the
# label for Branded, so per-100g is a safe assumption across dataTypes.
_USDA_NUTRIENT_MAP = {
    1008: "calories",        # Energy (kcal)
    1003: "protein",         # Protein (g)
    1004: "total_fat",       # Total lipid / fat (g)
    1258: "saturated_fat",   # Saturated fat (g)
    1257: "trans_fat",       # Trans fat (g)
    1253: "cholesterol",     # Cholesterol (mg)
    1093: "sodium",          # Sodium (mg)
    1005: "total_carbs",     # Carbohydrate, by difference (g)
    1079: "dietary_fiber",   # Fiber, total dietary (g)
    2000: "total_sugars",    # Total sugars (g)
    1235: "added_sugars",    # Added sugars (g)
    1110: "vitamin_d",       # Vitamin D (mcg)
    1087: "calcium",         # Calcium (mg)
    1089: "iron",            # Iron (mg)
    1092: "potassium",       # Potassium (mg)
}

# OFF stores mass nutrients in grams. NutritionData uses mg for most minerals
# and mcg for vitamin D. These multipliers convert from per-100g-in-grams to
# per-100g-in-target-unit.
_OFF_PER100G_FIELDS = {
    "calories": ("energy-kcal_100g", 1.0),
    "total_fat": ("fat_100g", 1.0),
    "saturated_fat": ("saturated-fat_100g", 1.0),
    "trans_fat": ("trans-fat_100g", 1.0),
    "cholesterol": ("cholesterol_100g", 1000.0),   # g → mg
    "sodium": ("sodium_100g", 1000.0),             # g → mg
    "total_carbs": ("carbohydrates_100g", 1.0),
    "dietary_fiber": ("fiber_100g", 1.0),
    "total_sugars": ("sugars_100g", 1.0),
    "added_sugars": ("added-sugars_100g", 1.0),
    "protein": ("proteins_100g", 1.0),
    "vitamin_d": ("vitamin-d_100g", 1_000_000.0),  # g → mcg
    "calcium": ("calcium_100g", 1000.0),           # g → mg
    "iron": ("iron_100g", 1000.0),                 # g → mg
    "potassium": ("potassium_100g", 1000.0),       # g → mg
}


def _usda_to_per_100g(food: dict) -> dict:
    """Extract per-100g nutrient values from a USDA foods[0] entry."""
    per_100g: dict = {}
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        field = _USDA_NUTRIENT_MAP.get(nid)
        if not field:
            continue
        try:
            per_100g[field] = float(n.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
    return per_100g


def _off_to_per_100g(product: dict) -> dict:
    """Extract per-100g nutrient values from an OFF product entry."""
    nutriments = product.get("nutriments", {}) or {}
    per_100g: dict = {}
    for field, (off_key, multiplier) in _OFF_PER100G_FIELDS.items():
        raw = nutriments.get(off_key)
        if raw is None:
            continue
        try:
            per_100g[field] = float(raw) * multiplier
        except (TypeError, ValueError):
            continue
    return per_100g


def _scale(per_100g: dict, grams: float) -> NutritionData:
    """Scale per-100g nutrient values to the requested portion size."""
    factor = max(0.0, grams) / 100.0
    return NutritionData(
        calories=per_100g.get("calories", 0.0) * factor,
        total_fat=per_100g.get("total_fat", 0.0) * factor,
        saturated_fat=per_100g.get("saturated_fat", 0.0) * factor,
        trans_fat=per_100g.get("trans_fat", 0.0) * factor,
        cholesterol=per_100g.get("cholesterol", 0.0) * factor,
        sodium=per_100g.get("sodium", 0.0) * factor,
        total_carbs=per_100g.get("total_carbs", 0.0) * factor,
        dietary_fiber=per_100g.get("dietary_fiber", 0.0) * factor,
        total_sugars=per_100g.get("total_sugars", 0.0) * factor,
        added_sugars=per_100g.get("added_sugars", 0.0) * factor,
        protein=per_100g.get("protein", 0.0) * factor,
        vitamin_d=per_100g.get("vitamin_d", 0.0) * factor,
        calcium=per_100g.get("calcium", 0.0) * factor,
        iron=per_100g.get("iron", 0.0) * factor,
        potassium=per_100g.get("potassium", 0.0) * factor,
        serving_size=f"{grams:.0f} g",
        servings_per_container=1.0,
    )


def lookup_food_nutrition(
    food_name: str, grams: float, api_key: str
) -> NutritionData | None:
    """Look up a food by name and scale its nutrition to the given portion.

    Uses the USDA + Open Food Facts fallback chain from
    `src.nutrition.usda_client.lookup_food`. Returns None if neither source
    has a match (caller should flag this to the user).

    Args:
        food_name: Food name from vision output (e.g. "grilled chicken breast").
        grams: Estimated portion size in grams.
        api_key: USDA FoodData Central API key.

    Returns:
        NutritionData scaled to `grams`, or None on miss.
    """
    if not food_name or grams <= 0:
        return None

    result = lookup_food(food_name, api_key)
    source = result.get("source")
    data = result.get("data", {})

    if source == "usda":
        foods = data.get("foods", [])
        if not foods:
            return None
        per_100g = _usda_to_per_100g(foods[0])
    elif source == "off":
        products = data.get("products", [])
        if not products:
            return None
        per_100g = _off_to_per_100g(products[0])
    else:
        return None

    if not per_100g:
        return None
    return _scale(per_100g, grams)


def aggregate_nutrition(
    food_items: list[dict], api_key: str
) -> NutritionData:
    """Combine multiple identified foods into a single NutritionData.

    For each item in `food_items` (output of `identify_food`), looks up
    nutrition via `lookup_food_nutrition` and sums the results. Missed
    foods (not in USDA or OFF) are flagged via `st.warning` so the user
    can correct the portion or name manually in the editor.

    Args:
        food_items: List of dicts with 'name' and 'estimated_grams' keys.
        api_key: USDA FoodData Central API key.

    Returns:
        Aggregated NutritionData across all successfully-looked-up items.
        If nothing could be looked up, returns an empty NutritionData.
    """
    if not food_items:
        return NutritionData()

    totals = {field: 0.0 for field in _USDA_NUTRIENT_MAP.values()}
    found_names: list[str] = []
    missed: list[str] = []

    for item in food_items:
        name = item.get("name", "")
        grams = float(item.get("estimated_grams", 0) or 0)
        nd = lookup_food_nutrition(name, grams, api_key)
        if nd is None:
            missed.append(name or "(unknown)")
            continue
        found_names.append(f"{name} ({grams:.0f}g)")
        totals["calories"] += nd.calories
        totals["total_fat"] += nd.total_fat
        totals["saturated_fat"] += nd.saturated_fat
        totals["trans_fat"] += nd.trans_fat
        totals["cholesterol"] += nd.cholesterol
        totals["sodium"] += nd.sodium
        totals["total_carbs"] += nd.total_carbs
        totals["dietary_fiber"] += nd.dietary_fiber
        totals["total_sugars"] += nd.total_sugars
        totals["added_sugars"] += nd.added_sugars
        totals["protein"] += nd.protein
        totals["vitamin_d"] += nd.vitamin_d
        totals["calcium"] += nd.calcium
        totals["iron"] += nd.iron
        totals["potassium"] += nd.potassium

    if missed:
        st.warning(
            "Could not find nutrition data for: "
            + ", ".join(missed)
            + ". Edit the values below to include them manually."
        )

    return NutritionData(
        calories=totals["calories"],
        total_fat=totals["total_fat"],
        saturated_fat=totals["saturated_fat"],
        trans_fat=totals["trans_fat"],
        cholesterol=totals["cholesterol"],
        sodium=totals["sodium"],
        total_carbs=totals["total_carbs"],
        dietary_fiber=totals["dietary_fiber"],
        total_sugars=totals["total_sugars"],
        added_sugars=totals["added_sugars"],
        protein=totals["protein"],
        vitamin_d=totals["vitamin_d"],
        calcium=totals["calcium"],
        iron=totals["iron"],
        potassium=totals["potassium"],
        serving_size="Full meal (sum of identified items)",
        servings_per_container=1.0,
        ingredients_list=", ".join(found_names),
    )
