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
    # ── Caloric Target ────────────────────────────────────────────────────────
    caloric_target = st.sidebar.number_input(
        "🎯 Daily Caloric Target (kcal)",
        min_value=500, max_value=5000,
        value=st.session_state.get("hp_caloric_target", 2000),
        step=50, key="hp_caloric_target",
    )

    # Visual calorie gauge
    gauge_pct = min(int(caloric_target / 2500 * 100), 100)
    gauge_color = (
        "#EF5350" if caloric_target > 3000
        else "#FFA726" if caloric_target > 2200
        else "#66BB6A"
    )
    st.sidebar.markdown(f"""
    <div style="margin:-4px 0 6px;">
        <div style="height:4px;background:rgba(128,128,128,0.2);
                    border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:{gauge_pct}%;
                        background:{gauge_color};border-radius:3px;"></div>
        </div>
        <div style="font-size:0.7rem;opacity:0.5;margin-top:3px;">
            {caloric_target} kcal vs 2,500 reference
        </div>
    </div>""", unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Profile Settings (collapsed to save space) ───────────────────────────
    with st.sidebar.expander("⚙️ Edit Profile Settings", expanded=False):
        allergens = st.multiselect(
            "⚠️ Allergens",
            options=COMMON_ALLERGENS,
            default=st.session_state.get("hp_allergens", []),
            key="hp_allergens",
            placeholder="None selected",
        )
        dietary_goals = st.multiselect(
            "🏃 Dietary Goals",
            options=DIETARY_GOALS,
            default=st.session_state.get("hp_dietary_goals", []),
            key="hp_dietary_goals",
            placeholder="None selected",
        )
        restrictions = st.multiselect(
            "🚫 Restrictions",
            options=DIETARY_RESTRICTIONS,
            default=st.session_state.get("hp_restrictions", []),
            key="hp_restrictions",
            placeholder="None selected",
        )

    profile = HealthProfile(
        caloric_target=caloric_target,
        dietary_goals=dietary_goals,
        allergens=allergens,
        restrictions=restrictions,
    )
    st.session_state["health_profile"] = profile

    # ── Active Profile summary ────────────────────────────────────────────────
    active_count = len(allergens) + len(dietary_goals) + len(restrictions)
    if active_count > 0:
        parts = []
        if allergens:
            short = allergens[:2] + ([f"+{len(allergens)-2}"] if len(allergens) > 2 else [])
            parts.append(f"⚠️ {', '.join(short)}")
        if dietary_goals:
            short = dietary_goals[:2] + ([f"+{len(dietary_goals)-2}"] if len(dietary_goals) > 2 else [])
            parts.append(f"🎯 {', '.join(short)}")
        if restrictions:
            short = restrictions[:2] + ([f"+{len(restrictions)-2}"] if len(restrictions) > 2 else [])
            parts.append(f"🚫 {', '.join(short)}")
        summary_text = " · ".join(parts)
        st.sidebar.caption(summary_text)

        if st.sidebar.button("✕ Clear Profile", key="clear_profile"):
            for k in ("hp_allergens", "hp_dietary_goals", "hp_restrictions"):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    else:
        st.sidebar.caption("No profile set — analysis will be generic")

    # ── Sidebar footer ────────────────────────────────────────────────────────
    st.sidebar.caption("NutriScan · Dataception 2026 · AI analysis for informational purposes only")

    return profile


# ── Section header helper ─────────────────────────────────────────────────────

def _section_header(icon: str, label: str,
                    color: str = "#4CAF50", border_color: str = "rgba(46,125,50,0.2)") -> None:
    """Render a styled section header within a form."""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;
                padding:0.35rem 0;margin:0.6rem 0 0.4rem;
                border-bottom:2px solid {border_color};">
        <span style="font-size:1rem;">{icon}</span>
        <span style="font-weight:700;font-size:0.88rem;color:{color};
                     letter-spacing:0.2px;">{label}</span>
    </div>""", unsafe_allow_html=True)


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
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;">
            <span style="font-size:1.4rem;">🏷️</span>
            <div>
                <div style="font-weight:800;font-size:1.05rem;color:#4CAF50;">
                    Nutrition Facts</div>
                <div style="font-size:0.78rem;color:inherit;opacity:0.7;">
                    Review and correct values, then click Confirm &amp; Analyze</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── Serving & Calories ───────────────────────────────────────────────
        _section_header("🍽️", "Serving & Calories")
        col1, col2, col3 = st.columns(3)
        with col1:
            serving_size = st.text_input(
                "Serving Size", value=nutrition_data.serving_size, key=k("serving_size")
            )
        with col2:
            servings_per_container = st.number_input(
                "Servings/Container",
                min_value=0.0, value=float(nutrition_data.servings_per_container),
                step=0.5, key=k("servings_per_container"),
            )
        with col3:
            calories = st.number_input(
                "Calories (kcal)", min_value=0.0, value=nutrition_data.calories,
                step=1.0, key=k("calories"),
            )

        # ── Fats ─────────────────────────────────────────────────────────────
        _section_header("🧈", "Fats & Cholesterol", color="#B71C1C", border_color="#FFCDD2")
        col1, col2 = st.columns(2)
        with col1:
            total_fat = st.number_input(
                "Total Fat (g)", min_value=0.0, value=nutrition_data.total_fat,
                step=0.1, key=k("total_fat"),
            )
            trans_fat = st.number_input(
                "Trans Fat (g)", min_value=0.0, value=nutrition_data.trans_fat,
                step=0.1, key=k("trans_fat"),
            )
        with col2:
            saturated_fat = st.number_input(
                "Saturated Fat (g)", min_value=0.0, value=nutrition_data.saturated_fat,
                step=0.1, key=k("saturated_fat"),
            )
            cholesterol = st.number_input(
                "Cholesterol (mg)", min_value=0.0, value=nutrition_data.cholesterol,
                step=1.0, key=k("cholesterol"),
            )

        # ── Carbs ─────────────────────────────────────────────────────────────
        _section_header("🍞", "Carbohydrates", color="#E65100", border_color="#FFE0B2")
        col1, col2 = st.columns(2)
        with col1:
            total_carbs = st.number_input(
                "Total Carbs (g)", min_value=0.0, value=nutrition_data.total_carbs,
                step=0.1, key=k("total_carbs"),
            )
            total_sugars = st.number_input(
                "Total Sugars (g)", min_value=0.0, value=nutrition_data.total_sugars,
                step=0.1, key=k("total_sugars"),
            )
        with col2:
            dietary_fiber = st.number_input(
                "Dietary Fiber (g)", min_value=0.0, value=nutrition_data.dietary_fiber,
                step=0.1, key=k("dietary_fiber"),
            )
            added_sugars = st.number_input(
                "Added Sugars (g)", min_value=0.0, value=nutrition_data.added_sugars,
                step=0.1, key=k("added_sugars"),
            )

        # ── Protein & Sodium ──────────────────────────────────────────────────
        _section_header("💪", "Protein & Sodium")
        col1, col2 = st.columns(2)
        with col1:
            protein = st.number_input(
                "Protein (g)", min_value=0.0, value=nutrition_data.protein,
                step=0.1, key=k("protein"),
            )
        with col2:
            sodium = st.number_input(
                "Sodium (mg)", min_value=0.0, value=nutrition_data.sodium,
                step=1.0, key=k("sodium"),
            )

        # ── Micronutrients ────────────────────────────────────────────────────
        _section_header("🌿", "Micronutrients", color="#1565C0", border_color="rgba(30,136,229,0.2)")
        col1, col2 = st.columns(2)
        with col1:
            vitamin_d = st.number_input(
                "Vitamin D (mcg)", min_value=0.0, value=nutrition_data.vitamin_d,
                step=0.1, key=k("vitamin_d"),
            )
            iron = st.number_input(
                "Iron (mg)", min_value=0.0, value=nutrition_data.iron,
                step=0.1, key=k("iron"),
            )
        with col2:
            calcium = st.number_input(
                "Calcium (mg)", min_value=0.0, value=nutrition_data.calcium,
                step=1.0, key=k("calcium"),
            )
            potassium = st.number_input(
                "Potassium (mg)", min_value=0.0, value=nutrition_data.potassium,
                step=1.0, key=k("potassium"),
            )

        ingredients_list = st.text_area(
            "📋 Ingredients List",
            value=nutrition_data.ingredients_list,
            height=90,
            key=k("ingredients_list"),
            help="Paste the full ingredients list from the label.",
            placeholder="e.g. Water, Enriched Flour, Sugar, Salt...",
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "✅ Confirm & Analyze", type="primary", use_container_width=True
        )

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

    return nutrition_data
