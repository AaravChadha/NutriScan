import json
import os
from src.nutrition.models import NutritionData

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "fda_daily_values.json")


def load_fda_values() -> dict:
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    # Return only nutrient values (exclude units metadata)
    return {k: v for k, v in data.items() if k != "units"}


def compute_dv_percentages(nutrition_data: NutritionData) -> dict:
    fda_values = load_fda_values()
    dv_percentages = {}

    nutrient_fields = {
        "calories": nutrition_data.calories,
        "total_fat": nutrition_data.total_fat,
        "saturated_fat": nutrition_data.saturated_fat,
        "cholesterol": nutrition_data.cholesterol,
        "sodium": nutrition_data.sodium,
        "total_carbs": nutrition_data.total_carbs,
        "dietary_fiber": nutrition_data.dietary_fiber,
        "added_sugars": nutrition_data.added_sugars,
        "protein": nutrition_data.protein,
        "vitamin_d": nutrition_data.vitamin_d,
        "calcium": nutrition_data.calcium,
        "iron": nutrition_data.iron,
        "potassium": nutrition_data.potassium,
    }

    for nutrient, amount in nutrient_fields.items():
        dv = fda_values.get(nutrient)
        if dv and dv > 0:
            dv_percentages[nutrient] = round((amount / dv) * 100, 1)

    return dv_percentages
