"""Manual Entry tab — enter nutrition data by hand and analyze it."""

import streamlit as st

from src.nutrition.fda_guidelines import compute_dv_percentages
from src.nutrition.models import HealthProfile, NutritionData
from src.ui.components import nutrition_editor
from src.ui.pages_results import results_display


def _init_session_state():
    if "manual_result" not in st.session_state:
        st.session_state.manual_result = None
    if "manual_dv" not in st.session_state:
        st.session_state.manual_dv = {}


def _run_analysis(nutrition_data: NutritionData) -> None:
    """Compute DV% and call LLM analyze(). Stores results in session_state.

    GroqClient.analyze() handles its own API/JSON errors via st.error and
    returns an empty AnalysisResult on failure, so the only exceptions we
    need to catch here are client construction failures (e.g. missing
    GROQ_API_KEY).
    """
    health_profile = st.session_state.get("health_profile", HealthProfile())
    dv = compute_dv_percentages(nutrition_data)

    try:
        from src.llm.groq_client import GroqClient
        client = GroqClient()
    except ValueError as e:
        st.error(str(e))
        st.session_state.manual_dv = dv
        return

    result = client.analyze(nutrition_data, health_profile, dv)
    st.session_state.manual_result = result
    st.session_state.manual_dv = dv
    st.rerun()


def render_manual_tab():
    """Main entry point for the Manual Entry tab."""
    st.header("Manual Entry")
    st.caption(
        "Enter nutrition information by hand — useful when you have a label "
        "in front of you or the scanner couldn't read it."
    )

    _init_session_state()

    # Always start from an empty NutritionData for fresh entry
    empty = NutritionData()
    confirmed = nutrition_editor(empty, key_prefix="manual")

    # nutrition_editor returns a new object on form submit
    if confirmed is not empty:
        st.session_state.manual_result = None
        st.session_state.manual_dv = {}
        with st.spinner("Analyzing..."):
            _run_analysis(confirmed)

    if st.session_state.manual_result is not None:
        st.divider()
        results_display(st.session_state.manual_result, st.session_state.manual_dv)
    elif st.session_state.manual_dv:
        # LLM not ready yet but DV% is available
        st.divider()
        st.subheader("% Daily Value Breakdown")
        import pandas as pd
        labels = {
            "calories": "Calories", "total_fat": "Total Fat",
            "saturated_fat": "Saturated Fat", "cholesterol": "Cholesterol",
            "sodium": "Sodium", "total_carbs": "Total Carbs",
            "dietary_fiber": "Dietary Fiber", "added_sugars": "Added Sugars",
            "protein": "Protein", "vitamin_d": "Vitamin D",
            "calcium": "Calcium", "iron": "Iron", "potassium": "Potassium",
        }
        df = (
            pd.DataFrame([
                {"Nutrient": labels.get(k, k), "% Daily Value": v}
                for k, v in st.session_state.manual_dv.items()
            ])
            .set_index("Nutrient")
        )
        st.bar_chart(df, color="#4CAF50")
