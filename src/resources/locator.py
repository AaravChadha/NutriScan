"""
Local food resource finder for food-insecure households.

Provides:
 - Nutrient gap analysis (6.1): compare user intake vs FDA daily values
 - Local resource lookup (6.2): find free/low-income food resources nearby
"""

from __future__ import annotations

from dataclasses import dataclass, field
from src.nutrition.models import NutritionData
from src.nutrition.fda_guidelines import load_fda_values


# ======================================================================
# 6.1  Nutrient Gap Analysis
# ======================================================================

# Threshold (% DV) below which a nutrient is considered deficient.
_LOW_THRESHOLD = 25.0

# 6.1.3  Mapping from nutrient → food categories that can fill the gap.
_NUTRIENT_FOOD_MAP: dict[str, list[str]] = {
    "calories":       ["whole grains", "legumes", "nuts", "peanut butter", "potatoes"],
    "total_fat":      ["nuts", "avocado", "olive oil", "peanut butter", "seeds"],
    "saturated_fat":  ["cheese", "butter", "coconut oil"],   # rarely deficient — included for completeness
    "cholesterol":    ["eggs", "shellfish"],                  # rarely deficient
    "sodium":         ["table salt", "canned soups"],         # almost never deficient
    "total_carbs":    ["bread", "rice", "pasta", "oats", "potatoes", "bananas"],
    "dietary_fiber":  ["beans", "lentils", "oats", "whole wheat bread", "broccoli", "apples"],
    "added_sugars":   [],  # not a gap to fill — sugar is a "limit" nutrient
    "protein":        ["eggs", "chicken", "canned tuna", "beans", "lentils", "peanut butter", "tofu"],
    "vitamin_d":      ["fortified milk", "fortified cereal", "canned salmon", "eggs", "sunlight exposure"],
    "calcium":        ["fortified milk", "yogurt", "cheese", "canned sardines", "leafy greens (kale, collards)"],
    "iron":           ["beans", "lentils", "fortified cereal", "spinach", "canned tuna", "tofu"],
    "potassium":      ["bananas", "potatoes", "sweet potatoes", "beans", "spinach", "tomato sauce"],
}

# Nutrients that are "limit" nutrients (high is bad, not low).
# We skip these when looking for deficiencies.
_LIMIT_NUTRIENTS = {"sodium", "saturated_fat", "cholesterol", "added_sugars"}


@dataclass
class NutrientGap:
    """A single nutrient deficiency."""
    nutrient: str           # e.g. "iron"
    current_pct_dv: float   # e.g. 12.5
    label: str              # human-readable, e.g. "Low on iron"
    food_suggestions: list[str] = field(default_factory=list)


@dataclass
class GapAnalysis:
    """Full gap analysis result."""
    gaps: list[NutrientGap] = field(default_factory=list)
    summary: str = ""


def analyze_nutrient_gaps(nutrition_data: NutritionData) -> GapAnalysis:
    """
    6.1.1  Compare user's scanned/entered foods against FDA daily values
           to identify deficiencies.

    Parameters:
        nutrition_data: aggregated NutritionData from the user's foods.

    Returns:
        GapAnalysis with a list of NutrientGap objects and a summary string.
    """

    fda_values = load_fda_values()

    nutrient_amounts = {
        "calories":       nutrition_data.calories,
        "total_fat":      nutrition_data.total_fat,
        "saturated_fat":  nutrition_data.saturated_fat,
        "cholesterol":    nutrition_data.cholesterol,
        "sodium":         nutrition_data.sodium,
        "total_carbs":    nutrition_data.total_carbs,
        "dietary_fiber":  nutrition_data.dietary_fiber,
        "added_sugars":   nutrition_data.added_sugars,
        "protein":        nutrition_data.protein,
        "vitamin_d":      nutrition_data.vitamin_d,
        "calcium":        nutrition_data.calcium,
        "iron":           nutrition_data.iron,
        "potassium":      nutrition_data.potassium,
    }

    gaps: list[NutrientGap] = []

    for nutrient, amount in nutrient_amounts.items():
        # Skip "limit" nutrients — being low on sodium is fine.
        if nutrient in _LIMIT_NUTRIENTS:
            continue

        dv = fda_values.get(nutrient)
        if not dv or dv <= 0:
            continue

        pct = round((amount / dv) * 100, 1)

        if pct < _LOW_THRESHOLD:
            # 6.1.2  Human-readable label
            pretty_name = nutrient.replace("_", " ").title()
            label = f"Low on {pretty_name} ({pct}% of Daily Value)"

            # 6.1.3  Map to food categories
            suggestions = _NUTRIENT_FOOD_MAP.get(nutrient, [])

            gaps.append(NutrientGap(
                nutrient=nutrient,
                current_pct_dv=pct,
                label=label,
                food_suggestions=list(suggestions),
            ))

    # Sort by severity (lowest %DV first)
    gaps.sort(key=lambda g: g.current_pct_dv)

    # 6.1.2  Generate summary
    if not gaps:
        summary = "Great news! Your intake meets or exceeds daily values across all key nutrients."
    else:
        names = [g.nutrient.replace("_", " ").title() for g in gaps]
        if len(names) <= 3:
            summary = f"Low on {', '.join(names)}."
        else:
            summary = f"Low on {', '.join(names[:3])}, and {len(names) - 3} more nutrient(s)."

    return GapAnalysis(gaps=gaps, summary=summary)
