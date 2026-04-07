"""Prompt templates for Groq LLM calls."""


def build_recipe_system_prompt() -> str:
    """System prompt for recipe generation from pantry items."""
    return (
        "You are a nutritionist and chef helping people combat food insecurity by "
        "making the most of the ingredients they have. Given a list of available "
        "ingredients (with optional nutrition data), the user's health profile, and "
        "dietary constraints, generate ONE practical, tasty recipe that:\n"
        "1. Uses primarily the ingredients available (minimize items not in the pantry)\n"
        "2. Respects all allergens and dietary restrictions\n"
        "3. Maximizes nutritional value given the user's goals\n"
        "4. Is simple to prepare (under 30 minutes, minimal equipment)\n"
        "5. Includes estimated per-serving nutrition breakdown\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "title": "Recipe Name",\n'
        '  "servings": 2,\n'
        '  "ingredients_used": ["ingredient 1 - amount", "ingredient 2 - amount"],\n'
        '  "additional_ingredients_needed": ["salt", "water"],\n'
        '  "instructions": ["Step 1...", "Step 2..."],\n'
        '  "estimated_nutrition_per_serving": {\n'
        '    "calories": 350, "total_fat": 12, "saturated_fat": 3,\n'
        '    "cholesterol": 45, "sodium": 480, "total_carbs": 40,\n'
        '    "dietary_fiber": 6, "total_sugars": 8, "added_sugars": 2,\n'
        '    "protein": 20, "vitamin_d": 0, "calcium": 150,\n'
        '    "iron": 3, "potassium": 400\n'
        "  },\n"
        '  "nutrition_highlights": ["High in protein", "Good source of fiber"],\n'
        '  "tips": "Storage and leftover tips..."\n'
        "}"
    )


def build_recipe_user_prompt(
    pantry_items: list[dict],
    health_profile: dict,
) -> str:
    """Build the user prompt for recipe generation.

    Args:
        pantry_items: List of dicts with 'name', 'quantity', and optional 'nutrition' dict.
        health_profile: Dict with 'caloric_target', 'allergens', 'restrictions', 'dietary_goals'.
    """
    items_text = ""
    for item in pantry_items:
        line = f"- {item['name']}"
        if item.get("quantity"):
            line += f" ({item['quantity']})"
        n = item.get("nutrition")
        if n:
            line += (
                f" [cal:{n.get('calories', 0)}, protein:{n.get('protein', 0)}g, "
                f"carbs:{n.get('total_carbs', 0)}g, fat:{n.get('total_fat', 0)}g]"
            )
        items_text += line + "\n"

    allergens = ", ".join(health_profile.get("allergens", [])) or "None"
    restrictions = ", ".join(health_profile.get("restrictions", [])) or "None"
    goals = ", ".join(health_profile.get("dietary_goals", [])) or "General health"
    caloric_target = health_profile.get("caloric_target", 2000)

    return (
        f"Available ingredients:\n{items_text}\n"
        f"Health profile:\n"
        f"Caloric target: {caloric_target} kcal/day\n"
        f"Allergens to avoid: {allergens}\n"
        f"Dietary restrictions: {restrictions}\n"
        f"Goals: {goals}\n\n"
        "Generate a recipe using these ingredients. Prioritize using what is available. "
        "Keep additional ingredients to common pantry staples (salt, pepper, oil, water). "
        "Focus on nutrition and simplicity."
    )
