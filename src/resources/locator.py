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
    "saturated_fat":  ["cheese", "butter", "coconut oil"],
    "cholesterol":    ["eggs", "shellfish"],
    "sodium":         ["table salt", "canned soups"],
    "total_carbs":    ["bread", "rice", "pasta", "oats", "potatoes", "bananas"],
    "dietary_fiber":  ["beans", "lentils", "oats", "whole wheat bread", "broccoli", "apples"],
    "added_sugars":   [],
    "protein":        ["eggs", "chicken", "canned tuna", "beans", "lentils", "peanut butter", "tofu"],
    "vitamin_d":      ["fortified milk", "fortified cereal", "canned salmon", "eggs"],
    "calcium":        ["fortified milk", "yogurt", "cheese", "canned sardines", "leafy greens (kale, collards)"],
    "iron":           ["beans", "lentils", "fortified cereal", "spinach", "canned tuna", "tofu"],
    "potassium":      ["bananas", "potatoes", "sweet potatoes", "beans", "spinach", "tomato sauce"],
}

# Nutrients that are "limit" nutrients (high is bad, not low).
_LIMIT_NUTRIENTS = {"sodium", "saturated_fat", "cholesterol", "added_sugars"}


@dataclass
class NutrientGap:
    """A single nutrient deficiency."""
    nutrient: str
    current_pct_dv: float
    label: str
    food_suggestions: list[str] = field(default_factory=list)


@dataclass
class GapAnalysis:
    """Full gap analysis result."""
    gaps: list[NutrientGap] = field(default_factory=list)
    summary: str = ""


def analyze_nutrient_gaps(nutrition_data: NutritionData) -> GapAnalysis:
    """6.1.1  Compare user's scanned/entered foods against FDA daily values.

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
        if nutrient in _LIMIT_NUTRIENTS:
            continue
        dv = fda_values.get(nutrient)
        if not dv or dv <= 0:
            continue
        pct = round((amount / dv) * 100, 1)
        if pct < _LOW_THRESHOLD:
            pretty_name = nutrient.replace("_", " ").title()
            label = f"Low on {pretty_name} ({pct}% of Daily Value)"
            gaps.append(NutrientGap(
                nutrient=nutrient,
                current_pct_dv=pct,
                label=label,
                food_suggestions=list(_NUTRIENT_FOOD_MAP.get(nutrient, [])),
            ))

    gaps.sort(key=lambda g: g.current_pct_dv)

    if not gaps:
        summary = "Great news! Your intake meets or exceeds daily values across all key nutrients."
    else:
        names = [g.nutrient.replace("_", " ").title() for g in gaps]
        if len(names) <= 3:
            summary = f"Low on {', '.join(names)}."
        else:
            summary = f"Low on {', '.join(names[:3])}, and {len(names) - 3} more nutrient(s)."

    return GapAnalysis(gaps=gaps, summary=summary)


# ======================================================================
# 6.2  Local Resource Lookup
# ======================================================================

RESOURCE_TYPES = [
    "food_bank",
    "food_pantry",
    "community_fridge",
    "community_garden",
    "snap_wic_retailer",
    "free_meal_program",
    "subsidized_farmers_market",
]

_TYPE_LABELS = {
    "food_bank": "Food Bank",
    "food_pantry": "Food Pantry",
    "community_fridge": "Community Fridge",
    "community_garden": "Community Garden",
    "snap_wic_retailer": "SNAP / WIC",
    "free_meal_program": "Free Meal Program",
    "subsidized_farmers_market": "Subsidized Farmers Market",
}

_TYPE_ICONS = {
    "food_bank": "🏦",
    "food_pantry": "🧺",
    "community_fridge": "🧊",
    "community_garden": "🌱",
    "snap_wic_retailer": "💳",
    "free_meal_program": "🍽️",
    "subsidized_farmers_market": "🥬",
}


@dataclass
class FoodResource:
    """A single free or low-income food resource."""
    name: str
    resource_type: str
    address: str
    city: str
    state: str
    zip_code: str
    hours: str
    phone: str = ""
    eligibility: str = ""
    website: str = ""
    notes: str = ""


# 6.2.5  Curated West Lafayette / Lafayette / Purdue area resources.
_CURATED_RESOURCES: list[FoodResource] = [
    FoodResource(
        name="Food Finders Food Bank",
        resource_type="food_bank",
        address="1204 Greenbush St",
        city="Lafayette", state="IN", zip_code="47904",
        hours="Mon–Fri 8:00 AM – 4:30 PM",
        phone="(765) 471-0062",
        eligibility="Open to all — no ID or proof of income required",
        website="https://www.foodfinders.org",
        notes="Largest food bank in the region. Distributes to 100+ partner agencies across 16 counties.",
    ),
    FoodResource(
        name="ACE Campus Food Pantry (Purdue)",
        resource_type="food_pantry",
        address="303 N University St, Purdue Memorial Union",
        city="West Lafayette", state="IN", zip_code="47907",
        hours="Mon–Fri 10:00 AM – 5:00 PM (academic year)",
        phone="(765) 494-5860",
        eligibility="Purdue students, staff, and their dependents — Purdue ID required",
        website="https://www.purdue.edu/vpsl/leadership/Initiatives/ace-campus-food-pantry.html",
        notes="Free groceries and personal care items. No questions asked about financial status.",
    ),
    FoodResource(
        name="St. Thomas Aquinas Food Pantry",
        resource_type="food_pantry",
        address="535 W State St",
        city="West Lafayette", state="IN", zip_code="47906",
        hours="Tue & Thu 1:00 PM – 3:00 PM",
        phone="(765) 743-1502",
        eligibility="Open to all in Greater Lafayette area",
        website="",
        notes="Walk-in pantry, no appointment needed.",
    ),
    FoodResource(
        name="Lafayette Urban Ministry Food Pantry",
        resource_type="food_pantry",
        address="525 N 4th St",
        city="Lafayette", state="IN", zip_code="47901",
        hours="Mon, Wed, Fri 12:00 PM – 3:00 PM",
        phone="(765) 423-2691",
        eligibility="Tippecanoe County residents — photo ID and proof of address",
        website="https://www.lumserve.org",
        notes="Also offers a free community lunch Mon–Fri 11 AM – 12:30 PM.",
    ),
    FoodResource(
        name="Lafayette Urban Ministry — Community Lunch",
        resource_type="free_meal_program",
        address="525 N 4th St",
        city="Lafayette", state="IN", zip_code="47901",
        hours="Mon–Fri 11:00 AM – 12:30 PM",
        phone="(765) 423-2691",
        eligibility="Open to all — no ID required",
        website="https://www.lumserve.org",
        notes="Free hot lunch, sit-down meal. Served daily.",
    ),
    FoodResource(
        name="Salvation Army — Community Meals",
        resource_type="free_meal_program",
        address="605 N 6th St",
        city="Lafayette", state="IN", zip_code="47901",
        hours="Mon–Sat 5:00 PM – 6:00 PM",
        phone="(765) 742-0006",
        eligibility="Open to all",
        website="",
        notes="Free dinner served nightly.",
    ),
    FoodResource(
        name="Tippecanoe County WIC Office",
        resource_type="snap_wic_retailer",
        address="629 N 6th St",
        city="Lafayette", state="IN", zip_code="47901",
        hours="Mon–Fri 8:00 AM – 4:30 PM",
        phone="(765) 423-9221",
        eligibility="Income-qualified pregnant/postpartum women, infants, and children under 5",
        website="https://www.in.gov/health/wic/",
        notes="WIC provides vouchers for milk, eggs, cereal, fruits/vegetables, and more.",
    ),
    FoodResource(
        name="Pay Less Super Market (SNAP accepted)",
        resource_type="snap_wic_retailer",
        address="2200 Elmwood Ave",
        city="Lafayette", state="IN", zip_code="47904",
        hours="Daily 6:00 AM – 11:00 PM",
        phone="(765) 447-2301",
        eligibility="SNAP/EBT accepted",
        website="",
        notes="Full grocery store accepting SNAP benefits.",
    ),
    FoodResource(
        name="Lafayette Community Garden — Columbian Park",
        resource_type="community_garden",
        address="1915 Scott St",
        city="Lafayette", state="IN", zip_code="47904",
        hours="Dawn to dusk (seasonal, Apr–Oct)",
        phone="",
        eligibility="Open to all Lafayette residents — plot fees waived for low-income",
        website="",
        notes="Free plots available for growing your own produce. Tools and seeds provided for first-time gardeners.",
    ),
    FoodResource(
        name="Purdue Student Farm — Free Produce Stand",
        resource_type="community_garden",
        address="1491 Cherry Ln",
        city="West Lafayette", state="IN", zip_code="47907",
        hours="Wed 3:00 PM – 5:00 PM (growing season)",
        phone="",
        eligibility="Open to all",
        website="",
        notes="Student-run farm. Free fresh produce distributed weekly during growing season.",
    ),
    FoodResource(
        name="Lafayette Farmers Market (Double Bucks SNAP)",
        resource_type="subsidized_farmers_market",
        address="5th St & Main St",
        city="Lafayette", state="IN", zip_code="47901",
        hours="Sat 7:30 AM – 12:30 PM (May–Oct)",
        phone="",
        eligibility="SNAP/EBT accepted — Double Bucks program doubles SNAP value up to $20",
        website="",
        notes="Fresh local produce, baked goods, eggs, and honey. SNAP dollars go twice as far here.",
    ),
]

_SUPPORTED_ZIPS = {
    "47901", "47902", "47903", "47904", "47905", "47906", "47907",
    "47909", "47920", "47970",
}


def find_local_resources(
    zip_code: str,
    resource_type: str | None = None,
) -> list[FoodResource]:
    """6.2.2  Find free/low-income food resources near a zip code.

    Parameters:
        zip_code:      5-digit US zip code.
        resource_type: optional filter — one of RESOURCE_TYPES, or None/"all"
                       to return all types.

    Returns:
        List of FoodResource objects. Currently uses the curated West Lafayette
        / Lafayette fallback (6.2.5). Returns empty list for unsupported zips.
    """
    zip_code = zip_code.strip()[:5]

    if zip_code not in _SUPPORTED_ZIPS:
        return []

    results = list(_CURATED_RESOURCES)

    if resource_type and resource_type != "all":
        results = [r for r in results if r.resource_type == resource_type]

    return results


def get_supported_zip_codes() -> set[str]:
    """Return the set of zip codes with curated resource data."""
    return set(_SUPPORTED_ZIPS)


def type_label(resource_type: str) -> str:
    """Human-readable label for a resource type."""
    return _TYPE_LABELS.get(resource_type, resource_type.replace("_", " ").title())


def type_icon(resource_type: str) -> str:
    """Emoji icon for a resource type."""
    return _TYPE_ICONS.get(resource_type, "📍")