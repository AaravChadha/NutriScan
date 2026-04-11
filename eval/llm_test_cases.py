"""
Test cases for Phase 5.1 LLM evaluation.

Each case is a (nutrition, health profile, expectations) triple that gets
run through the full LLM analysis pipeline in `eval/llm_accuracy.py`.
The five cases deliberately exercise different dimensions of the analysis
prompt so we can score per-dimension pass/fail for the poster:

    1. Clean pass        — healthy food + general profile → low risk, no flags
    2. Allergen          — user allergen listed in ingredients → high risk + specific flag
    3. Preservatives     — multiple additives present → multi-flag preservative section
    4. Goal conflict     — low-sodium goal vs very high sodium product → explicit CONFLICT
    5. Multi-issue       — cascading: allergen + preservative + nutrient + goal all fire

Nutrition values are anchored to realistic public-facing labels so the
LLM's flagging reflects what a nutritionist would actually say about a
real product. Expectations use substring matching (case-insensitive) on
the fields of the returned AnalysisResult — we want "does it catch the
concept" not "does the wording match exactly", because the LLM phrases
things differently across runs.
"""

# Each test case is a dict with:
#   id           — short stable identifier for the report
#   description  — one-line intent of the case
#   nutrition    — kwargs for NutritionData (any missing field defaults to 0)
#   profile      — kwargs for HealthProfile
#   expected     — dict of substring checks + risk range + min recommendations
TEST_CASES: list[dict] = [
    # ------------------------------------------------------------------
    # 1. Clean pass — baseline. Plain rolled oats, general health profile.
    # The LLM should recognize this as a low-risk, nutritionally sound
    # product and NOT invent allergens or preservatives that aren't there.
    # ------------------------------------------------------------------
    {
        "id": "1_clean_pass_oats",
        "description": (
            "Plain rolled oats, general health profile — baseline. "
            "LLM should return low risk, empty allergen/preservative lists, "
            "and a positive goal alignment."
        ),
        "nutrition": {
            "calories": 150,
            "total_fat": 2.5,
            "saturated_fat": 0.5,
            "trans_fat": 0,
            "cholesterol": 0,
            "sodium": 0,
            "total_carbs": 27,
            "dietary_fiber": 4,
            "total_sugars": 1,
            "added_sugars": 0,
            "protein": 5,
            "vitamin_d": 0,
            "calcium": 20,
            "iron": 1.7,
            "potassium": 150,
            "serving_size": "1/2 cup dry (40g)",
            "servings_per_container": 13,
            "ingredients_list": "Whole grain rolled oats.",
        },
        "profile": {
            "caloric_target": 2000,
            "dietary_goals": ["general health"],
            "allergens": [],
            "restrictions": [],
        },
        "expected": {
            "allergen_terms": [],
            "preservative_terms": [],
            "nutrient_flag_terms": [],       # fiber at 4g isn't "notably low" for a 40g serving
            "goal_conflict_terms": [],
            "risk_in": {"low"},
            "min_recommendations": 1,
            # Strong negative: we must NOT hallucinate allergens or preservatives
            "forbidden_allergen_terms": ["wheat", "soy", "dairy", "egg"],
            "forbidden_preservative_terms": ["BHT", "BHA", "TBHQ"],
        },
    },

    # ------------------------------------------------------------------
    # 2. Allergen — peanut butter cup product, user has peanut allergy.
    # Must flag peanut by name and escalate risk to high. Also contains
    # milk, so dairy should appear too (user didn't list it, but the LLM
    # prompt says to flag listed ingredients regardless).
    # ------------------------------------------------------------------
    {
        "id": "2_allergen_peanut",
        "description": (
            "Peanut butter cup for a peanut-allergic user. Must flag "
            "peanut specifically and return high overall risk."
        ),
        "nutrition": {
            "calories": 210,
            "total_fat": 13,
            "saturated_fat": 5,
            "trans_fat": 0,
            "cholesterol": 5,
            "sodium": 150,
            "total_carbs": 24,
            "dietary_fiber": 2,
            "total_sugars": 21,
            "added_sugars": 20,
            "protein": 5,
            "vitamin_d": 0,
            "calcium": 30,
            "iron": 0.7,
            "potassium": 140,
            "serving_size": "2 cups (42g)",
            "servings_per_container": 1,
            "ingredients_list": (
                "Milk chocolate (sugar, cocoa butter, chocolate, "
                "nonfat milk, milk fat, lactose, soy lecithin), "
                "peanuts, sugar, dextrose, salt, TBHQ (preservative)."
            ),
        },
        "profile": {
            "caloric_target": 2000,
            "dietary_goals": ["general health"],
            "allergens": ["peanut"],
            "restrictions": [],
        },
        "expected": {
            "allergen_terms": ["peanut"],
            "preservative_terms": ["TBHQ"],  # bonus if the LLM also catches this
            "nutrient_flag_terms": ["sugar"],
            "goal_conflict_terms": [],       # no specific goal to conflict with
            "risk_in": {"high"},
            "min_recommendations": 1,
            "forbidden_allergen_terms": [],
        },
    },

    # ------------------------------------------------------------------
    # 3. Preservatives — snack chips with a stack of additives. User has
    # no allergens. The preservative flag list should catch BHT, BHA,
    # TBHQ, or some subset thereof. Risk should be moderate.
    # ------------------------------------------------------------------
    {
        "id": "3_preservatives_chips",
        "description": (
            "Fried snack with BHT + BHA + TBHQ. No user allergens. "
            "Must flag preservatives and surface sodium/saturated fat."
        ),
        "nutrition": {
            "calories": 160,
            "total_fat": 10,
            "saturated_fat": 1.5,
            "trans_fat": 0,
            "cholesterol": 0,
            "sodium": 170,
            "total_carbs": 15,
            "dietary_fiber": 1,
            "total_sugars": 0,
            "added_sugars": 0,
            "protein": 2,
            "vitamin_d": 0,
            "calcium": 0,
            "iron": 0.4,
            "potassium": 350,
            "serving_size": "1 oz (28g)",
            "servings_per_container": 8,
            "ingredients_list": (
                "Potatoes, vegetable oil (sunflower, corn, and/or canola oil), "
                "salt, BHT, BHA, TBHQ."
            ),
        },
        "profile": {
            "caloric_target": 2000,
            "dietary_goals": ["general health"],
            "allergens": [],
            "restrictions": [],
        },
        "expected": {
            "allergen_terms": [],
            "preservative_terms": ["BHT", "BHA", "TBHQ"],
            "nutrient_flag_terms": [],  # single serving isn't egregious on any one nutrient
            "goal_conflict_terms": [],
            "risk_in": {"moderate", "high"},
            "min_recommendations": 1,
        },
    },

    # ------------------------------------------------------------------
    # 4. Goal conflict — instant ramen + low-sodium dietary goal. Sodium
    # is ~80% DV so the LLM should flag nutrient AND surface an explicit
    # low-sodium goal conflict in goal_alignment.
    # ------------------------------------------------------------------
    {
        "id": "4_goal_conflict_low_sodium",
        "description": (
            "Instant ramen for a user with a low-sodium dietary goal. "
            "Must flag sodium as a nutrient concern AND as a goal CONFLICT."
        ),
        "nutrition": {
            "calories": 380,
            "total_fat": 14,
            "saturated_fat": 7,
            "trans_fat": 0,
            "cholesterol": 0,
            "sodium": 1820,
            "total_carbs": 52,
            "dietary_fiber": 2,
            "total_sugars": 2,
            "added_sugars": 0,
            "protein": 8,
            "vitamin_d": 0,
            "calcium": 20,
            "iron": 4,
            "potassium": 230,
            "serving_size": "1 package (85g)",
            "servings_per_container": 1,
            "ingredients_list": (
                "Enriched wheat flour, palm oil, salt, potato starch, "
                "soy sauce powder, monosodium glutamate, dehydrated onion, "
                "garlic powder, caramel color."
            ),
        },
        "profile": {
            "caloric_target": 2000,
            "dietary_goals": ["low sodium"],
            "allergens": [],
            "restrictions": [],
        },
        "expected": {
            "allergen_terms": [],
            "preservative_terms": [],
            "nutrient_flag_terms": ["sodium"],
            "goal_conflict_terms": ["sodium"],  # "low sodium goal: CONFLICT ..."
            "risk_in": {"high"},                # 80% DV sodium is a serious flag
            "min_recommendations": 1,
        },
    },

    # ------------------------------------------------------------------
    # 5. Multi-issue — sugary chocolate-milk cereal for a user who is
    # lactose-intolerant (restriction) AND trying to cut added sugars.
    # Should fire across allergen/preservative/nutrient/goal dimensions.
    # ------------------------------------------------------------------
    {
        "id": "5_multi_issue_cereal",
        "description": (
            "Sugary chocolate-milk kids cereal for a lactose-intolerant user "
            "with a low-added-sugar goal. Expect cascading flags across "
            "allergen, preservative, nutrient, and goal-alignment dimensions."
        ),
        "nutrition": {
            "calories": 160,
            "total_fat": 1.5,
            "saturated_fat": 0,
            "trans_fat": 0,
            "cholesterol": 0,
            "sodium": 230,
            "total_carbs": 34,
            "dietary_fiber": 3,
            "total_sugars": 18,
            "added_sugars": 17,
            "protein": 2,
            "vitamin_d": 4,
            "calcium": 250,
            "iron": 8,
            "potassium": 90,
            "serving_size": "1 cup (40g) with 1/2 cup skim milk",
            "servings_per_container": 10,
            "ingredients_list": (
                "Whole grain corn, sugar, corn syrup, cocoa processed with "
                "alkali, canola oil, nonfat milk, salt, natural and artificial "
                "flavors, red 40, yellow 5, BHT (preservative added to "
                "preserve freshness)."
            ),
        },
        "profile": {
            "caloric_target": 2000,
            "dietary_goals": ["low added sugar"],
            "allergens": [],
            "restrictions": ["lactose-intolerant"],
        },
        "expected": {
            "allergen_terms": ["milk"],           # nonfat milk is in ingredients
            "preservative_terms": ["BHT"],
            "nutrient_flag_terms": ["added sugar", "sugar"],
            "goal_conflict_terms": ["sugar"],     # low-added-sugar goal CONFLICT
            "risk_in": {"moderate", "high"},
            "min_recommendations": 2,
        },
    },
]


def load_test_cases() -> list[dict]:
    """Return the evaluation test cases.

    Kept as a function so callers (eval runners, unit tests) import a
    stable entry point instead of the module-level constant, in case we
    later switch to loading from JSON or a spreadsheet.
    """
    return TEST_CASES
