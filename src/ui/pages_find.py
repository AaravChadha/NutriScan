"""Find Free Food Near You tab — nutrient gap analysis + local resource finder."""

import streamlit as st

from src.resources.locator import (
    FoodResource,
    GapAnalysis,
    analyze_nutrient_gaps,
    find_local_resources,
    type_icon,
    type_label,
)
from src.nutrition.models import NutritionData

_RESOURCE_TYPE_OPTIONS = {
    "All": None,
    "Food Banks": "food_bank",
    "Food Pantries": "food_pantry",
    "Free Meals": "free_meal_program",
    "SNAP / WIC": "snap_wic_retailer",
    "Community Gardens": "community_garden",
    "Farmers Markets": "subsidized_farmers_market",
}


def _init_session_state():
    if "find_resources" not in st.session_state:
        st.session_state.find_resources = []
    if "find_advice" not in st.session_state:
        st.session_state.find_advice = None
    if "find_zip" not in st.session_state:
        st.session_state.find_zip = ""


def _get_best_nutrition() -> NutritionData | None:
    """Return the most recent scanned NutritionData from any tab, or None."""
    for key in ("upload_nutrition", "snap_nutrition", "manual_nutrition"):
        nd = st.session_state.get(key)
        if nd and isinstance(nd, NutritionData) and nd.calories > 0:
            return nd
    return None


def _render_nutrient_gap_summary() -> list[dict]:
    """Render the nutrient gap section. Returns gaps as dicts for the LLM prompt."""
    st.subheader("Nutrient Gap Summary")

    nutrition = _get_best_nutrition()

    if nutrition is None:
        st.info(
            "No scan data found. Use the Upload Label, Snap Food, or Manual Entry "
            "tabs to scan a food item first — your gaps will appear here."
        )
        return []

    analysis: GapAnalysis = analyze_nutrient_gaps(nutrition)

    if not analysis.gaps:
        st.success(analysis.summary)
        return []

    st.caption(
        f"{analysis.summary}  \n"
        "Based on your most recent food scan. A single item won't cover your full "
        "daily intake — these gaps reflect that item's contribution."
    )

    col1, col2 = st.columns(2)
    for i, gap in enumerate(analysis.gaps):
        col = col1 if i % 2 == 0 else col2
        with col:
            color = "🔴" if gap.current_pct_dv < 10 else "🟡"
            st.metric(
                label=f"{color} {gap.nutrient.replace('_', ' ').title()}",
                value=f"{gap.current_pct_dv}% DV",
                delta=gap.label.split("(")[0].strip(),
                delta_color="inverse",
            )

    # Convert to dicts for the LLM prompt
    return [
        {
            "nutrient": g.nutrient,
            "current_pct_dv": g.current_pct_dv,
            "label": g.label,
            "food_suggestions": g.food_suggestions,
        }
        for g in analysis.gaps
    ]


def _render_resource_list(resources: list[FoodResource]):
    """Render resource cards."""
    if not resources:
        st.warning(
            "No resources found for this zip code. "
            "Try a West Lafayette / Lafayette zip (e.g. 47906, 47901) for the demo, "
            "or check 211.org for resources near you."
        )
        return

    st.subheader(f"Free Food Resources ({len(resources)} found)")

    for r in resources:
        icon = type_icon(r.resource_type)
        label = type_label(r.resource_type)
        with st.expander(f"{icon} {r.name} — {label}"):
            col_info, col_contact = st.columns([2, 1])
            with col_info:
                st.markdown(f"**Address:** {r.address}, {r.city}, {r.state} {r.zip_code}")
                st.markdown(f"**Hours:** {r.hours}")
                st.markdown(f"**Eligibility:** {r.eligibility}")
                if r.notes:
                    st.caption(r.notes)
            with col_contact:
                if r.phone:
                    st.markdown(f"**Phone:** {r.phone}")
                if r.website:
                    st.markdown(f"**Website:** {r.website}")


def _resource_to_dict(r: FoodResource) -> dict:
    """Convert a FoodResource to the dict format expected by the LLM prompt."""
    return {
        "name": r.name,
        "resource_type": r.resource_type,
        "address": r.address,
        "city": r.city,
        "hours": r.hours,
        "eligibility": r.eligibility,
        "notes": r.notes,
    }


def _render_llm_advice(gaps: list[dict], resources: list[FoodResource]):
    """Render the personalized LLM recommendation section."""
    st.subheader("Personalized Advice")

    if not resources:
        st.info("Find resources above to get personalized advice.")
        return

    existing = st.session_state.find_advice
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        label = "Refresh Advice" if existing else "Get Personalized Advice"
        run = st.button(label, type="primary", key="find_get_advice")

    if run:
        with st.spinner("Generating personalized recommendations..."):
            try:
                from src.llm.groq_client import GroqClient
                client = GroqClient()
                resource_dicts = [_resource_to_dict(r) for r in resources]
                advice = client.recommend_resources(gaps, resource_dicts)
                st.session_state.find_advice = advice
                st.rerun()
            except Exception as e:
                st.error(f"Could not generate advice: {e}")

    advice = st.session_state.find_advice
    if advice:
        if advice.get("summary"):
            st.info(advice["summary"])
        for tip in advice.get("tips", []):
            st.markdown(f"- {tip}")
        st.caption(
            "*Advice is AI-generated for informational purposes. "
            "Verify hours and eligibility directly with each resource.*"
        )


def render_find_tab():
    """Main entry point for the Find Free Food Near You tab."""
    st.header("Find Free Food Near You")
    st.caption(
        "Enter your zip code to find free food banks, pantries, meal programs, "
        "and benefits near you. If you've scanned a food item, we'll also show "
        "which nutrients you may be missing and where to find them for free."
    )

    _init_session_state()

    # ── Zip code + filter ─────────────────────────────────────────────────────
    col_zip, col_type, col_btn = st.columns([2, 2, 1])
    with col_zip:
        zip_code = st.text_input(
            "Zip Code",
            value=st.session_state.find_zip,
            placeholder="e.g. 47906",
            max_chars=5,
            key="find_zip_input",
        )
    with col_type:
        type_choice = st.selectbox(
            "Resource Type",
            options=list(_RESOURCE_TYPE_OPTIONS.keys()),
            key="find_type_filter",
        )
    with col_btn:
        st.write("")
        st.write("")
        search = st.button("Find Resources", type="primary", key="find_search_btn")

    if search and zip_code:
        if len(zip_code) != 5 or not zip_code.isdigit():
            st.error("Please enter a valid 5-digit zip code.")
        else:
            resource_type = _RESOURCE_TYPE_OPTIONS[type_choice]
            resources = find_local_resources(zip_code, resource_type)
            st.session_state.find_resources = resources
            st.session_state.find_zip = zip_code
            st.session_state.find_advice = None
            st.rerun()

    st.divider()

    # ── Nutrient gap summary ──────────────────────────────────────────────────
    gaps = _render_nutrient_gap_summary()

    st.divider()

    # ── Resource list ─────────────────────────────────────────────────────────
    resources: list[FoodResource] = st.session_state.find_resources
    if not resources and not st.session_state.find_zip:
        st.info(
            "Enter a zip code above and click **Find Resources** to see "
            "what's available near you."
        )
    else:
        _render_resource_list(resources)

        if resources:
            st.divider()
            _render_llm_advice(gaps, resources)