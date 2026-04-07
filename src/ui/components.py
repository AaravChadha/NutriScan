"""Reusable Streamlit widgets shared across pages."""

import streamlit as st

from src.nutrition.models import HealthProfile, NutritionData

# ── Constants ─────────

COMMON_ALLERGENS = [
    "Peanuts", "Tree Nuts", "Milk", "Eggs", "Wheat", "Soy",
    "Fish", "Shellfish", "Sesame",
]

DIETARY_GOALS = [
    "Low Sodium", "Low Sugar", "High Protein", "Low Fat",
    "High Fiber", "Low Calorie", "Heart Healthy", "Diabetic Friendly",
]

DIETARY_RESTRICTIONS = [
    "Vegan", "Vegetarian", "Gluten-Free", "Dairy-Free",
    "Halal", "Kosher", "Nut-Free",
]


# ── Health Profile Form (sidebar) ────────────────────────────────────────────

def health_profile_form() -> HealthProfile:
    """
    Render the health profile form in the sidebar.
    Stores the profile in st.session_state["health_profile"].
    Returns the current HealthProfile object.
    """
    st.sidebar.header("Your Health Profile")
    st.sidebar.caption("Optional — improves analysis accuracy.")

    caloric_target = st.sidebar.number_input(
        "Daily Caloric Target (kcal)",
        min_value=500,
        max_value=5000,
        value=st.session_state.get("hp_caloric_target", 2000),
        step=50,
        key="hp_caloric_target",
    )

    allergens = st.sidebar.multiselect(
        "Allergens",
        options=COMMON_ALLERGENS,
        default=st.session_state.get("hp_allergens", []),
        key="hp_allergens",
    )

    dietary_goals = st.sidebar.multiselect(
        "Dietary Goals",
        options=DIETARY_GOALS,
        default=st.session_state.get("hp_dietary_goals", []),
        key="hp_dietary_goals",
    )

    restrictions = st.sidebar.multiselect(
        "Dietary Restrictions",
        options=DIETARY_RESTRICTIONS,
        default=st.session_state.get("hp_restrictions", []),
        key="hp_restrictions",
    )

    profile = HealthProfile(
        caloric_target=caloric_target,
        dietary_goals=dietary_goals,
        allergens=allergens,
        restrictions=restrictions,
    )
    st.session_state["health_profile"] = profile
    return profile


# ── Nutrition Editor ─────────────────────────────────────────────────────────

def nutrition_editor(nutrition_data: NutritionData, key_prefix: str = "") -> NutritionData:
    """
    Render an editable form pre-filled with nutrition_data values.
    key_prefix avoids Streamlit widget key collisions across pages.
    Returns a corrected NutritionData on submit.
    """
    def k(name: str) -> str:
        return f"{key_prefix}_{name}" if key_prefix else name

    with st.form(key=k("nutrition_form")):
        st.subheader("Nutrition Facts")

        col1, col2 = st.columns(2)

        with col1:
            serving_size = st.text_input(
                "Serving Size", value=nutrition_data.serving_size, key=k("serving_size")
            )
            servings_per_container = st.number_input(
                "Servings per Container",
                min_value=0.0, value=float(nutrition_data.servings_per_container),
                step=0.5, key=k("servings_per_container"),
            )
            calories = st.number_input(
                "Calories (kcal)", min_value=0.0, value=nutrition_data.calories,
                step=1.0, key=k("calories"),
            )
            total_fat = st.number_input(
                "Total Fat (g)", min_value=0.0, value=nutrition_data.total_fat,
                step=0.1, key=k("total_fat"),
            )
            saturated_fat = st.number_input(
                "Saturated Fat (g)", min_value=0.0, value=nutrition_data.saturated_fat,
                step=0.1, key=k("saturated_fat"),
            )
            trans_fat = st.number_input(
                "Trans Fat (g)", min_value=0.0, value=nutrition_data.trans_fat,
                step=0.1, key=k("trans_fat"),
            )
            cholesterol = st.number_input(
                "Cholesterol (mg)", min_value=0.0, value=nutrition_data.cholesterol,
                step=1.0, key=k("cholesterol"),
            )
            sodium = st.number_input(
                "Sodium (mg)", min_value=0.0, value=nutrition_data.sodium,
                step=1.0, key=k("sodium"),
            )

        with col2:
            total_carbs = st.number_input(
                "Total Carbohydrates (g)", min_value=0.0, value=nutrition_data.total_carbs,
                step=0.1, key=k("total_carbs"),
            )
            dietary_fiber = st.number_input(
                "Dietary Fiber (g)", min_value=0.0, value=nutrition_data.dietary_fiber,
                step=0.1, key=k("dietary_fiber"),
            )
            total_sugars = st.number_input(
                "Total Sugars (g)", min_value=0.0, value=nutrition_data.total_sugars,
                step=0.1, key=k("total_sugars"),
            )
            added_sugars = st.number_input(
                "Added Sugars (g)", min_value=0.0, value=nutrition_data.added_sugars,
                step=0.1, key=k("added_sugars"),
            )
            protein = st.number_input(
                "Protein (g)", min_value=0.0, value=nutrition_data.protein,
                step=0.1, key=k("protein"),
            )
            vitamin_d = st.number_input(
                "Vitamin D (mcg)", min_value=0.0, value=nutrition_data.vitamin_d,
                step=0.1, key=k("vitamin_d"),
            )
            calcium = st.number_input(
                "Calcium (mg)", min_value=0.0, value=nutrition_data.calcium,
                step=1.0, key=k("calcium"),
            )
            iron = st.number_input(
                "Iron (mg)", min_value=0.0, value=nutrition_data.iron,
                step=0.1, key=k("iron"),
            )
            potassium = st.number_input(
                "Potassium (mg)", min_value=0.0, value=nutrition_data.potassium,
                step=1.0, key=k("potassium"),
            )

        ingredients_list = st.text_area(
            "Ingredients List",
            value=nutrition_data.ingredients_list,
            height=100,
            key=k("ingredients_list"),
            help="Paste the full ingredients list from the label.",
        )

        submitted = st.form_submit_button("Confirm & Analyze", type="primary")

    if submitted:
        return NutritionData(
            calories=calories,
            total_fat=total_fat,
            saturated_fat=saturated_fat,
            trans_fat=trans_fat,
            cholesterol=cholesterol,
            sodium=sodium,
            total_carbs=total_carbs,
            dietary_fiber=dietary_fiber,
            total_sugars=total_sugars,
            added_sugars=added_sugars,
            protein=protein,
            vitamin_d=vitamin_d,
            calcium=calcium,
            iron=iron,
            potassium=potassium,
            serving_size=serving_size,
            servings_per_container=servings_per_container,
            ingredients_list=ingredients_list,
        )

    # Return original (unchanged) if not submitted
    return nutrition_data