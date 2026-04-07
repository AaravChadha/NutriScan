"""Groq API client for LLM-powered analysis and recipe generation."""

import json
import os
import time

from dotenv import load_dotenv
from groq import Groq

from src.nutrition.models import (
    AnalysisResult,
    GeneratedRecipe,
    HealthProfile,
    NutritionData,
    PantryItem,
)
from src.llm.prompts import build_recipe_system_prompt, build_recipe_user_prompt

load_dotenv()

NUTRITION_FIELDS = [
    "calories", "total_fat", "saturated_fat", "cholesterol", "sodium",
    "total_carbs", "dietary_fiber", "total_sugars", "added_sugars",
    "protein", "vitamin_d", "calcium", "iron", "potassium",
]


class GroqClient:
    """Wrapper around the Groq API."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables.")
        self.client = Groq(api_key=api_key)

    def _call_with_retry(self, messages: list[dict], temperature: float = 0.3, max_retries: int = 2) -> str:
        """Call Groq chat completion with retry on rate limit."""
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise
        return ""

    def generate_recipe(
        self,
        pantry_items: list[PantryItem],
        health_profile: HealthProfile,
    ) -> GeneratedRecipe:
        """Generate a recipe from pantry items and health profile."""
        items_dicts = []
        for item in pantry_items:
            d: dict = {"name": item.name, "quantity": item.quantity}
            if item.nutrition:
                d["nutrition"] = {
                    "calories": item.nutrition.calories,
                    "protein": item.nutrition.protein,
                    "total_carbs": item.nutrition.total_carbs,
                    "total_fat": item.nutrition.total_fat,
                }
            items_dicts.append(d)

        profile_dict = {
            "caloric_target": health_profile.caloric_target,
            "allergens": health_profile.allergens,
            "restrictions": health_profile.restrictions,
            "dietary_goals": health_profile.dietary_goals,
        }

        messages = [
            {"role": "system", "content": build_recipe_system_prompt()},
            {"role": "user", "content": build_recipe_user_prompt(items_dicts, profile_dict)},
        ]

        raw = self._call_with_retry(messages, temperature=0.5)
        data = json.loads(raw)

        # Parse estimated nutrition into NutritionData
        est = data.get("estimated_nutrition_per_serving", {})
        estimated_nutrition = NutritionData(
            **{k: float(est.get(k, 0)) for k in NUTRITION_FIELDS}
        )

        return GeneratedRecipe(
            title=data.get("title", "Untitled Recipe"),
            servings=data.get("servings", 1),
            ingredients_used=data.get("ingredients_used", []),
            additional_ingredients_needed=data.get("additional_ingredients_needed", []),
            instructions=data.get("instructions", []),
            estimated_nutrition=estimated_nutrition,
            nutrition_highlights=data.get("nutrition_highlights", []),
            tips=data.get("tips", ""),
        )
