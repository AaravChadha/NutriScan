"""Unit tests for LLM prompt construction and response parsing."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.llm.prompts import (
    build_analysis_system_prompt,
    build_analysis_user_prompt,
)
from src.nutrition.models import AnalysisResult, HealthProfile, NutritionData


# ---------- 3.2.3.1 — Prompt construction ----------


def test_system_prompt_includes_json_schema_keys():
    """System prompt must list every required AnalysisResult field."""
    prompt = build_analysis_system_prompt()
    for key in [
        "allergen_flags",
        "preservative_flags",
        "nutrient_flags",
        "goal_alignment",
        "recommendations",
        "overall_risk",
        "summary",
    ]:
        assert key in prompt, f"system prompt missing schema key: {key}"


def test_system_prompt_mentions_core_responsibilities():
    prompt = build_analysis_system_prompt().lower()
    assert "allergen" in prompt
    assert "preservative" in prompt
    assert "daily value" in prompt or "dv" in prompt
    assert "json" in prompt


def test_user_prompt_includes_nutrition_values():
    nutrition = {
        "calories": 250,
        "total_fat": 12,
        "saturated_fat": 4,
        "trans_fat": 0,
        "cholesterol": 30,
        "sodium": 480,
        "total_carbs": 28,
        "dietary_fiber": 3,
        "total_sugars": 8,
        "added_sugars": 5,
        "protein": 9,
        "vitamin_d": 0,
        "calcium": 100,
        "iron": 2,
        "potassium": 200,
        "serving_size": "1 cup (240g)",
        "servings_per_container": 2,
        "ingredients_list": "wheat, sugar, salt, BHT",
    }
    dv = {"sodium": 21, "saturated_fat": 20, "added_sugars": 10}
    profile = {
        "caloric_target": 1800,
        "dietary_goals": ["low sodium"],
        "allergens": ["peanut"],
        "restrictions": ["vegetarian"],
    }

    prompt = build_analysis_user_prompt(nutrition, dv, profile)

    # Nutrition facts surface
    assert "250" in prompt  # calories
    assert "480" in prompt  # sodium
    assert "1 cup (240g)" in prompt  # serving size
    # DV% surfaces inline
    assert "21% DV" in prompt
    # Ingredients surface
    assert "BHT" in prompt
    # Profile surfaces
    assert "1800" in prompt
    assert "peanut" in prompt
    assert "vegetarian" in prompt
    assert "low sodium" in prompt


def test_user_prompt_handles_empty_profile_fields():
    """Empty allergens/restrictions/goals should not crash and render as 'None'."""
    nutrition = {
        "calories": 100,
        "serving_size": "",
        "servings_per_container": 1,
        "ingredients_list": "",
    }
    profile = {
        "caloric_target": 2000,
        "dietary_goals": [],
        "allergens": [],
        "restrictions": [],
    }

    prompt = build_analysis_user_prompt(nutrition, {}, profile)

    assert "Allergens to avoid: None" in prompt
    assert "Dietary restrictions: None" in prompt
    assert "not specified" in prompt  # serving size fallback
    assert "not provided" in prompt  # ingredients fallback


# ---------- 3.2.3.2 — Response parsing ----------


def _mock_groq_response(payload: dict):
    """Build a fake Groq chat completion response containing payload as JSON."""
    fake = MagicMock()
    fake.choices = [MagicMock()]
    fake.choices[0].message.content = json.dumps(payload)
    return fake


def test_analyze_parses_valid_json_into_analysis_result():
    payload = {
        "allergen_flags": ["peanut: listed in ingredients"],
        "preservative_flags": ["BHT: synthetic antioxidant"],
        "nutrient_flags": ["sodium: 35% DV (high)"],
        "goal_alignment": ["low-sodium goal: CONFLICT"],
        "recommendations": ["Limit to half a serving", "Pair with vegetables"],
        "overall_risk": "moderate",
        "summary": "High sodium and contains an allergen for this user.",
    }

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), \
         patch("src.llm.groq_client.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(payload)
        )

        from src.llm.groq_client import GroqClient

        client = GroqClient()
        result = client.analyze(
            NutritionData(calories=250, sodium=800),
            HealthProfile(allergens=["peanut"], dietary_goals=["low sodium"]),
            {"sodium": 35},
        )

    assert isinstance(result, AnalysisResult)
    assert result.allergen_flags == ["peanut: listed in ingredients"]
    assert result.preservative_flags == ["BHT: synthetic antioxidant"]
    assert result.nutrient_flags == ["sodium: 35% DV (high)"]
    assert result.goal_alignment == ["low-sodium goal: CONFLICT"]
    assert len(result.recommendations) == 2
    assert result.overall_risk == "moderate"
    assert "sodium" in result.summary.lower()


def test_analyze_handles_missing_fields_with_defaults():
    """Partial JSON should still produce a valid AnalysisResult."""
    payload = {"summary": "Looks fine.", "overall_risk": "low"}

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), \
         patch("src.llm.groq_client.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(payload)
        )

        from src.llm.groq_client import GroqClient

        client = GroqClient()
        result = client.analyze(NutritionData(), HealthProfile(), {})

    assert result.allergen_flags == []
    assert result.preservative_flags == []
    assert result.overall_risk == "low"
    assert result.summary == "Looks fine."


def test_analyze_returns_empty_result_on_invalid_json():
    """Bad JSON from the model should not crash — return empty AnalysisResult."""
    fake = MagicMock()
    fake.choices = [MagicMock()]
    fake.choices[0].message.content = "not valid json {{{"

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), \
         patch("src.llm.groq_client.Groq") as MockGroq, \
         patch("src.llm.groq_client.st") as mock_st:
        MockGroq.return_value.chat.completions.create.return_value = fake

        from src.llm.groq_client import GroqClient

        client = GroqClient()
        result = client.analyze(NutritionData(), HealthProfile(), {})

    assert isinstance(result, AnalysisResult)
    assert result.allergen_flags == []
    assert result.overall_risk == "unknown"
    mock_st.error.assert_called_once()
