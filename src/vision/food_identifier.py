"""Food identification from photos using Groq's vision API.

Given raw image bytes (JPEG/PNG), calls a Groq vision model to identify
each food/beverage item and estimate its portion in grams. Used by the
Snap Food tab (`src/ui/pages_snap.py`).
"""

import base64
import json
import os
import re

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from src.llm.prompts import build_vision_system_prompt, build_vision_user_prompt

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
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

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
