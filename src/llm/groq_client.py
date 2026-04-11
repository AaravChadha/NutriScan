"""Groq API client for LLM-powered analysis and recipe generation."""

import json
import os
import time

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from src.nutrition.models import (
    AnalysisResult,
    GeneratedRecipe,
    HealthProfile,
    NutritionData,
    PantryItem,
)
from src.llm.prompts import (
    build_analysis_system_prompt,
    build_analysis_user_prompt,
    build_recipe_system_prompt,
    build_recipe_user_prompt,
    build_resource_recommendation_system_prompt,
    build_resource_recommendation_user_prompt,
)

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

    def analyze(
        self,
        nutrition_data: NutritionData,
        health_profile: HealthProfile,
        dv_percentages: dict,
    ) -> AnalysisResult:
        """Analyze a nutrition label for a specific user.

        Returns an AnalysisResult with allergen/preservative/nutrient flags,
        goal alignment, recommendations, overall risk, and a summary.
        On API failure, surfaces a user-friendly error via st.error and
        returns an empty AnalysisResult so the UI does not crash.
        """
        nutrition_dict = {
            "calories": nutrition_data.calories,
            "total_fat": nutrition_data.total_fat,
            "saturated_fat": nutrition_data.saturated_fat,
            "trans_fat": nutrition_data.trans_fat,
            "cholesterol": nutrition_data.cholesterol,
            "sodium": nutrition_data.sodium,
            "total_carbs": nutrition_data.total_carbs,
            "dietary_fiber": nutrition_data.dietary_fiber,
            "total_sugars": nutrition_data.total_sugars,
            "added_sugars": nutrition_data.added_sugars,
            "protein": nutrition_data.protein,
            "vitamin_d": nutrition_data.vitamin_d,
            "calcium": nutrition_data.calcium,
            "iron": nutrition_data.iron,
            "potassium": nutrition_data.potassium,
            "serving_size": nutrition_data.serving_size,
            "servings_per_container": nutrition_data.servings_per_container,
            "ingredients_list": nutrition_data.ingredients_list,
        }

        profile_dict = {
            "caloric_target": health_profile.caloric_target,
            "dietary_goals": health_profile.dietary_goals,
            "allergens": health_profile.allergens,
            "restrictions": health_profile.restrictions,
        }

        messages = [
            {"role": "system", "content": build_analysis_system_prompt()},
            {
                "role": "user",
                "content": build_analysis_user_prompt(
                    nutrition_dict, dv_percentages, profile_dict
                ),
            },
        ]

        try:
            raw = self._call_with_retry(messages, temperature=0.3)
            data = json.loads(raw)
        except json.JSONDecodeError:
            st.error("The AI returned an invalid response. Please try again.")
            return AnalysisResult()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return AnalysisResult()

        return AnalysisResult(
            allergen_flags=data.get("allergen_flags", []),
            preservative_flags=data.get("preservative_flags", []),
            nutrient_flags=data.get("nutrient_flags", []),
            goal_alignment=data.get("goal_alignment", []),
            recommendations=data.get("recommendations", []),
            overall_risk=data.get("overall_risk", "unknown"),
            summary=data.get("summary", ""),
        )

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

    def recommend_resources(
        self,
        nutrient_gaps: list[dict],
        local_resources: list[dict],
    ) -> dict:
        """Generate personalized free-resource recommendations.

        6.3.1 + 6.3.2  Uses the LLM to connect nutrient gaps to specific
        local free food resources with actionable advice.

        Args:
            nutrient_gaps: list of dicts from NutrientGap dataclasses.
            local_resources: list of dicts from FoodResource dataclasses.

        Returns:
            Dict with 'personalized_recommendations', 'general_tips',
            and 'summary'.
        """
        messages = [
            {"role": "system", "content": build_resource_recommendation_system_prompt()},
            {
                "role": "user",
                "content": build_resource_recommendation_user_prompt(
                    nutrient_gaps, local_resources
                ),
            },
        ]

        try:
            raw = self._call_with_retry(messages, temperature=0.4)
            data = json.loads(raw)
        except json.JSONDecodeError:
            st.error("The AI returned an invalid response. Please try again.")
            return {
                "personalized_recommendations": [],
                "general_tips": [],
                "summary": "Unable to generate recommendations at this time.",
            }
        except Exception as e:
            st.error(f"Resource recommendation failed: {e}")
            return {
                "personalized_recommendations": [],
                "general_tips": [],
                "summary": "Unable to generate recommendations at this time.",
            }

        return {
            "personalized_recommendations": data.get("personalized_recommendations", []),
            "general_tips": data.get("general_tips", []),
            "summary": data.get("summary", ""),
        }
