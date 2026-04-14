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
    """Compute DV% and call LLM analyze(). Stores results in session_state."""
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
    st.markdown("""
    <div style="margin-bottom:0.75rem;">
        <div style="font-size:1.25rem;font-weight:800;color:#1B5E20;">✏️ Manual Entry</div>
        <div style="font-size:0.85rem;color:#666;margin-top:2px;">
            Enter nutrition values by hand — useful when you have a label in front of you
            or the scanner couldn't read it clearly.
        </div>
    </div>""", unsafe_allow_html=True)

    # Quick-start tip card
    st.markdown("""
    <div style="background:#E8F5E9;border-radius:12px;padding:0.8rem 1.1rem;
                margin-bottom:1rem;display:flex;align-items:flex-start;gap:10px;">
        <span style="font-size:1.2rem;flex-shrink:0;">💡</span>
        <div style="font-size:0.84rem;color:#1B5E20;line-height:1.55;">
            <strong>Tip:</strong> Fill in as many fields as you have — unknown values can stay at 0.
            The AI analysis works best with calories, sodium, fat, and ingredients.
        </div>
    </div>""", unsafe_allow_html=True)

    _init_session_state()

    empty = NutritionData()
    confirmed = nutrition_editor(empty, key_prefix="manual")

    if confirmed is not empty:
        st.session_state.manual_result = None
        st.session_state.manual_dv = {}
        with st.spinner("🧠 Analyzing nutrition..."):
            _run_analysis(confirmed)

    if st.session_state.manual_result is not None:
        st.divider()
        results_display(st.session_state.manual_result, st.session_state.manual_dv)
    elif st.session_state.manual_dv:
        import pandas as pd
        st.divider()
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
