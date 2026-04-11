"""Prompt templates for Groq LLM calls."""


def build_vision_system_prompt() -> str:
    """System prompt for food photo identification (Snap Food tab).

    Instructs the vision model to identify every distinct food or beverage
    in the image, estimate each portion in grams, assign a confidence
    score, and return a strict JSON object. Used by `food_identifier.py`
    with `llama-3.2-90b-vision-preview`.
    """
    return (
        "You are a nutritionist analyzing a photo of food. Your job is to "
        "identify every distinct food or beverage item visible in the image "
        "and estimate the portion size of each one in grams.\n\n"
        "Rules:\n"
        "1. ONLY identify items you can actually see. Do not guess hidden "
        "ingredients (e.g. don't assume a sandwich has mayo unless it is "
        "visible). Do not hallucinate items that are not in the image.\n"
        "2. Use common food names that would match a USDA or Open Food Facts "
        "search — e.g. 'grilled chicken breast', 'white rice', 'broccoli', "
        "'whole milk'. Avoid overly specific brand names unless clearly "
        "visible on the packaging.\n"
        "3. Combine obvious components of a dish into one item when that is "
        "how it would be looked up (e.g. 'cheese pizza slice', not separate "
        "'dough', 'cheese', 'tomato sauce'). Split clearly separate items "
        "on the plate (e.g. 'grilled chicken' + 'mashed potatoes' + 'green "
        "beans').\n"
        "4. For portion estimation, use standard reference portions when "
        "uncertain (1 cup cooked rice ≈ 160g, 1 medium apple ≈ 180g, 1 "
        "chicken breast ≈ 170g, 1 slice bread ≈ 30g). Be conservative — if "
        "you cannot tell whether a portion is large or small, lean toward "
        "a typical single serving rather than guessing at extremes.\n"
        "5. Assign each item a `confidence` score from 0.0 to 1.0 based on "
        "how certain you are about BOTH the identity and the portion. Use "
        "below 0.5 if you are genuinely unsure — the user can correct it.\n"
        "6. Exclude plates, bowls, utensils, napkins, and other non-food "
        "objects. Beverages ARE food — include them.\n\n"
        "Return ONLY valid JSON with this exact structure (no markdown, no "
        "prose outside the JSON):\n"
        "{\n"
        '  "foods": [\n'
        "    {\n"
        '      "name": "grilled chicken breast",\n'
        '      "estimated_grams": 170,\n'
        '      "confidence": 0.85\n'
        "    },\n"
        "    {\n"
        '      "name": "steamed broccoli",\n'
        '      "estimated_grams": 90,\n'
        '      "confidence": 0.9\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "If the image contains no identifiable food, return "
        '`{"foods": []}`. Never invent items to fill the array.'
    )


def build_vision_user_prompt() -> str:
    """User prompt that accompanies the image content block.

    The heavy lifting is done by the system prompt + the image itself;
    this is a short nudge to produce the JSON.
    """
    return (
        "Identify every food and beverage item in this photo, estimate each "
        "portion in grams, and return the JSON object as specified."
    )


def build_analysis_system_prompt() -> str:
    """System prompt for nutrition label analysis.

    Instructs the model to flag allergens, preservatives, and nutrient
    concerns, evaluate goal alignment, and return a strict JSON object.
    """
    return (
        "You are a registered dietitian and food scientist analyzing a nutrition "
        "label for a specific user. You will receive parsed nutrition facts, "
        "FDA Daily Value percentages, an ingredients list, and the user's health "
        "profile (caloric target, dietary goals, allergens, restrictions).\n\n"
        "Your job:\n"
        "1. ALLERGENS — Cross-reference the ingredients against the user's allergens. "
        "Flag any direct matches AND common derivatives (e.g. 'whey' for dairy, "
        "'lecithin' for soy). Be conservative: when in doubt, flag it.\n"
        "2. PRESERVATIVES & ADDITIVES — Identify artificial preservatives, "
        "colorings, and additives of concern (BHA, BHT, sodium nitrite, "
        "potassium bromate, artificial dyes, high-fructose corn syrup, etc.).\n"
        "3. NUTRIENT FLAGS — Use the DV% values to flag nutrients that are very "
        "high (>=20% DV for sodium, saturated fat, added sugars) or notably low "
        "where they should be high (fiber, protein, key vitamins/minerals).\n"
        "4. GOAL ALIGNMENT — For each of the user's dietary goals, state whether "
        "this product supports or conflicts with that goal, and why.\n"
        "5. RECOMMENDATIONS — Give 2-4 short, actionable recommendations tailored "
        "to this user (e.g. 'Pair with a high-fiber side', 'Limit to one serving').\n"
        "6. OVERALL RISK — One of: 'low', 'moderate', 'high'. Base this on the "
        "combined severity of allergen, preservative, and nutrient flags for "
        "THIS user specifically.\n"
        "7. SUMMARY — One or two plain-language sentences the user can read at "
        "a glance.\n\n"
        "Return ONLY valid JSON with this exact structure (no markdown, no prose "
        "outside the JSON):\n"
        "{\n"
        '  "allergen_flags": ["peanut: listed in ingredients", "..."],\n'
        '  "preservative_flags": ["BHT: synthetic antioxidant", "..."],\n'
        '  "nutrient_flags": ["sodium: 35% DV per serving (high)", "..."],\n'
        '  "goal_alignment": ["low-sodium goal: CONFLICT — 35% DV sodium", "..."],\n'
        '  "recommendations": ["Limit to half a serving", "..."],\n'
        '  "overall_risk": "moderate",\n'
        '  "summary": "Plain-language one-liner for the user."\n'
        "}\n"
        "All fields are required. Use empty arrays ([]) when nothing applies. "
        "Never invent ingredients or nutrients that were not provided."
    )


def build_analysis_user_prompt(
    nutrition_data: dict,
    dv_percentages: dict,
    health_profile: dict,
) -> str:
    """Build the user prompt for nutrition label analysis.

    Args:
        nutrition_data: Dict of NutritionData fields (calories, total_fat, ...,
            ingredients_list, serving_size, servings_per_container).
        dv_percentages: Dict mapping nutrient name -> percent of FDA daily value.
        health_profile: Dict with 'caloric_target', 'dietary_goals',
            'allergens', 'restrictions'.
    """
    serving_size = nutrition_data.get("serving_size") or "not specified"
    servings_per_container = nutrition_data.get("servings_per_container", 1)
    ingredients = nutrition_data.get("ingredients_list") or "not provided"

    nutrient_keys = [
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
    units = {
        "calories": "kcal",
        "cholesterol": "mg",
        "sodium": "mg",
        "vitamin_d": "mcg",
        "calcium": "mg",
        "iron": "mg",
        "potassium": "mg",
    }

    nutrition_lines = []
    for key in nutrient_keys:
        value = nutrition_data.get(key, 0)
        unit = units.get(key, "g")
        dv = dv_percentages.get(key)
        dv_str = f" ({dv:.0f}% DV)" if dv is not None else ""
        nutrition_lines.append(f"- {key.replace('_', ' ')}: {value} {unit}{dv_str}")
    nutrition_text = "\n".join(nutrition_lines)

    allergens = ", ".join(health_profile.get("allergens", [])) or "None"
    restrictions = ", ".join(health_profile.get("restrictions", [])) or "None"
    goals = ", ".join(health_profile.get("dietary_goals", [])) or "General health"
    caloric_target = health_profile.get("caloric_target", 2000)

    return (
        f"NUTRITION FACTS (per serving)\n"
        f"Serving size: {serving_size}\n"
        f"Servings per container: {servings_per_container}\n"
        f"{nutrition_text}\n\n"
        f"INGREDIENTS\n{ingredients}\n\n"
        f"USER HEALTH PROFILE\n"
        f"Caloric target: {caloric_target} kcal/day\n"
        f"Dietary goals: {goals}\n"
        f"Allergens to avoid: {allergens}\n"
        f"Dietary restrictions: {restrictions}\n\n"
        "Analyze this product for THIS user and return the JSON object as specified."
    )


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
