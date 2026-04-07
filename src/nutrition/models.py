from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NutritionData:
    calories: float = 0.0
    total_fat: float = 0.0
    saturated_fat: float = 0.0
    trans_fat: float = 0.0
    cholesterol: float = 0.0
    sodium: float = 0.0
    total_carbs: float = 0.0
    dietary_fiber: float = 0.0
    total_sugars: float = 0.0
    added_sugars: float = 0.0
    protein: float = 0.0
    vitamin_d: float = 0.0
    calcium: float = 0.0
    iron: float = 0.0
    potassium: float = 0.0
    serving_size: str = ""
    servings_per_container: float = 1.0
    ingredients_list: str = ""


@dataclass
class HealthProfile:
    caloric_target: int = 2000
    dietary_goals: list[str] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    allergen_flags: list[str] = field(default_factory=list)
    preservative_flags: list[str] = field(default_factory=list)
    nutrient_flags: list[str] = field(default_factory=list)
    goal_alignment: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    overall_risk: str = "unknown"
    summary: str = ""


@dataclass
class PantryItem:
    name: str = ""
    source: str = ""  # "label_scan" | "photo_id" | "manual"
    nutrition: Optional[NutritionData] = None
    estimated_grams: Optional[float] = None
    quantity: str = ""


@dataclass
class GeneratedRecipe:
    title: str = ""
    servings: int = 1
    ingredients_used: list[str] = field(default_factory=list)
    additional_ingredients_needed: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    estimated_nutrition: Optional[NutritionData] = None
    nutrition_highlights: list[str] = field(default_factory=list)
    tips: str = ""
