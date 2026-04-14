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

# Color scheme per resource type: (card_bg, text_color, left_border, badge_bg, badge_text)
_TYPE_COLORS = {
    "food_bank":                ("#FAFCFF", "#1565C0", "#1976D2", "#E3F2FD", "#1565C0"),
    "food_pantry":              ("#F9FDF9", "#1B5E20", "#2E7D32", "#E8F5E9", "#1B5E20"),
    "free_meal_program":        ("#FFFAF5", "#BF360C", "#F57C00", "#FFF3E0", "#E65100"),
    "snap_wic_retailer":        ("#FAF5FF", "#6A1B9A", "#7B1FA2", "#F3E5F5", "#6A1B9A"),
    "community_garden":         ("#FAFEF5", "#558B2F", "#689F38", "#F1F8E9", "#558B2F"),
    "subsidized_farmers_market":("#F5FEFF", "#00695C", "#00838F", "#E0F7FA", "#00695C"),
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


def _render_search_bar() -> tuple[str, str, bool]:
    """Render the zip code + type filter search bar. Returns (zip_code, type_choice, search_clicked)."""
    st.markdown("""
    <div style="font-weight:700;font-size:0.92rem;color:#1B5E20;
                margin-bottom:0.6rem;display:flex;align-items:center;gap:7px;">
        🔍 Search for Free Food Resources
    </div>""", unsafe_allow_html=True)

    col_zip, col_type, col_btn = st.columns([2, 2, 1])
    with col_zip:
        zip_code = st.text_input(
            "📮 Zip Code",
            value=st.session_state.find_zip,
            placeholder="e.g. 47906",
            max_chars=5,
            key="find_zip_input",
        )
    with col_type:
        type_choice = st.selectbox(
            "🏷️ Resource Type",
            options=list(_RESOURCE_TYPE_OPTIONS.keys()),
            key="find_type_filter",
        )
    with col_btn:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        search = st.button("🔍 Search", type="primary", key="find_search_btn", use_container_width=True)

    # Demo hint
    demo_cols = st.columns([3, 1])
    with demo_cols[1]:
        if st.button("📍 Try West Lafayette", key="demo_zip", use_container_width=True):
            st.session_state.find_zip = "47906"
            st.rerun()

    return zip_code, type_choice, search


def _render_nutrient_gap_summary() -> list[dict]:
    """Render the nutrient gap section. Returns gaps as dicts for the LLM prompt."""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;padding:0.35rem 0;
                margin-bottom:0.75rem;border-bottom:2px solid #C8E6C9;">
        <span style="font-size:1rem;">🔬</span>
        <span style="font-weight:700;font-size:0.95rem;color:#1B5E20;">
            Nutrient Gap Summary
        </span>
        <span style="font-size:0.76rem;color:#888;font-style:italic;">
            — based on your most recent scan
        </span>
    </div>""", unsafe_allow_html=True)

    nutrition = _get_best_nutrition()

    if nutrition is None:
        st.markdown("""
        <div style="background:#F9FDF9;border:1px dashed #C8E6C9;border-radius:12px;
                    padding:1.1rem 1.4rem;color:#6A8A6A;font-size:0.87rem;
                    display:flex;align-items:center;gap:12px;">
            <span style="font-size:1.8rem;">💡</span>
            <div>
                <strong>No scan data yet.</strong><br>
                Use <strong>Upload Label</strong>, <strong>Snap Food</strong>, or
                <strong>Manual Entry</strong> first — your nutrient gaps will appear here
                and guide which foods to look for at local resources.
            </div>
        </div>""", unsafe_allow_html=True)
        return []

    analysis: GapAnalysis = analyze_nutrient_gaps(nutrition)

    if not analysis.gaps:
        st.markdown(f"""
        <div style="background:#E8F5E9;border:1px solid #66BB6A;border-radius:12px;
                    padding:1rem 1.25rem;color:#1B5E20;font-size:0.9rem;
                    display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.5rem;">✅</span>
            <span><strong>{analysis.summary}</strong></span>
        </div>""", unsafe_allow_html=True)
        return []

    st.markdown(f"""
    <div style="background:#FFF8E1;border-left:4px solid #FFB300;
                border-radius:0 10px 10px 0;padding:0.65rem 1rem;
                font-size:0.84rem;color:#666;margin-bottom:0.8rem;line-height:1.5;">
        {analysis.summary} — A single food item won't cover a full day's intake.
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for i, gap in enumerate(analysis.gaps):
        col = col1 if i % 2 == 0 else col2
        with col:
            is_critical = gap.current_pct_dv < 10
            icon = "🔴" if is_critical else "🟡"
            bg = "#FFEBEE" if is_critical else "#FFF8E1"
            border = "#EF5350" if is_critical else "#FFB300"
            color = "#B71C1C" if is_critical else "#E65100"
            track_pct = min(gap.current_pct_dv, 100)
            bar_color = "#EF5350" if is_critical else "#FFA726"

            # Food suggestions for this gap
            suggestions = gap.food_suggestions[:3] if hasattr(gap, "food_suggestions") and gap.food_suggestions else []
            suggestions_html = ""
            if suggestions:
                suggestion_chips = " ".join(
                    f'<span style="background:rgba(255,255,255,0.6);'
                    f'border-radius:100px;padding:1px 8px;font-size:0.7rem;">'
                    f'{s}</span>'
                    for s in suggestions
                )
                suggestions_html = f'<div style="margin-top:5px;">{suggestion_chips}</div>'

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};border-radius:12px;
                        padding:0.8rem 1rem;margin-bottom:0.5rem;">
                <div style="font-size:0.75rem;font-weight:700;color:{color};
                            opacity:0.75;text-transform:uppercase;letter-spacing:0.5px;">
                    {icon} {gap.nutrient.replace('_', ' ').title()}
                </div>
                <div style="font-size:1.4rem;font-weight:800;color:{color};
                            margin:2px 0;">
                    {gap.current_pct_dv}% DV
                </div>
                <div style="height:5px;background:rgba(0,0,0,0.08);
                            border-radius:3px;overflow:hidden;margin:5px 0;">
                    <div style="height:100%;width:{track_pct}%;
                                background:{bar_color};border-radius:3px;"></div>
                </div>
                <div style="font-size:0.77rem;color:{color};opacity:0.8;">
                    {gap.label.split("(")[0].strip()}
                </div>
                {suggestions_html}
            </div>""", unsafe_allow_html=True)

    return [
        {
            "nutrient": g.nutrient,
            "current_pct_dv": g.current_pct_dv,
            "label": g.label,
            "food_suggestions": g.food_suggestions if hasattr(g, "food_suggestions") else [],
        }
        for g in analysis.gaps
    ]


def _render_resource_list(resources: list[FoodResource]):
    if not resources:
        st.markdown("""
        <div style="background:#FFF8E1;border:1px solid #FFB300;border-radius:12px;
                    padding:1.25rem 1.5rem;color:#E65100;font-size:0.87rem;
                    line-height:1.55;">
            <strong>⚠️ No resources found for this zip code.</strong><br>
            Try a West Lafayette / Lafayette zip (e.g. <code>47906</code>, <code>47901</code>)
            for the demo, or check
            <strong>211.org</strong> for resources in your area.
        </div>""", unsafe_allow_html=True)
        return

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;padding:0.35rem 0;
                margin-bottom:0.75rem;border-bottom:2px solid #C8E6C9;">
        <span style="font-size:1rem;">📍</span>
        <span style="font-weight:700;font-size:0.95rem;color:#1B5E20;">
            Free Food Resources
        </span>
        <span style="background:#E8F5E9;color:#2E7D32;padding:1px 10px;
                     border-radius:100px;font-size:0.75rem;font-weight:700;">
            {len(resources)} found
        </span>
    </div>""", unsafe_allow_html=True)

    for r in resources:
        icon = type_icon(r.resource_type)
        lbl = type_label(r.resource_type)
        card_bg, _, border_c, badge_bg, badge_text = _TYPE_COLORS.get(
            r.resource_type, ("#FAFAFA", "#424242", "#9E9E9E", "#F5F5F5", "#616161")
        )

        phone_html = (
            f'<span style="margin-left:12px;">📞 {r.phone}</span>'
            if r.phone else ""
        )
        website_html = (
            f'<div style="margin-top:6px;">'
            f'<a href="{r.website}" target="_blank" '
            f'style="color:{border_c};font-size:0.82rem;font-weight:600;'
            f'text-decoration:none;">🌐 Visit website →</a></div>'
            if r.website else ""
        )
        notes_html = (
            f'<div style="margin-top:6px;font-size:0.79rem;color:#888;'
            f'font-style:italic;padding-top:5px;border-top:1px solid rgba(0,0,0,0.06);">'
            f'ℹ️ {r.notes}</div>'
            if r.notes else ""
        )

        st.markdown(f"""
        <div style="background:{card_bg};border-radius:14px;
                    padding:1.1rem 1.4rem 0.9rem;
                    box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    margin-bottom:0.75rem;border-left:5px solid {border_c};">
            <div style="display:flex;align-items:flex-start;
                        justify-content:space-between;margin-bottom:0.55rem;
                        flex-wrap:wrap;gap:4px;">
                <span style="font-size:1.0rem;font-weight:800;color:#1A2E1A;">
                    {icon} {r.name}
                </span>
                <span style="background:{badge_bg};color:{badge_text};
                             padding:2px 10px;border-radius:100px;
                             font-size:0.7rem;font-weight:700;white-space:nowrap;">
                    {lbl}
                </span>
            </div>
            <div style="font-size:0.85rem;color:#444;line-height:1.65;">
                <div>📍 {r.address}, {r.city}, {r.state} {r.zip_code}</div>
                <div>🕐 {r.hours}</div>
                <div>👥 {r.eligibility}{phone_html}</div>
            </div>
            {website_html}
            {notes_html}
        </div>""", unsafe_allow_html=True)


def _resource_to_dict(r: FoodResource) -> dict:
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
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;padding:0.35rem 0;
                margin-bottom:0.75rem;border-bottom:2px solid #C8E6C9;">
        <span style="font-size:1rem;">💡</span>
        <span style="font-weight:700;font-size:0.95rem;color:#1B5E20;">
            Personalized Advice
        </span>
    </div>""", unsafe_allow_html=True)

    if not resources:
        st.markdown("""
        <div style="background:#F9FDF9;border:1px dashed #C8E6C9;border-radius:12px;
                    padding:1rem;color:#888;font-size:0.87rem;">
            Find resources above to get personalized nutrition + access advice.
        </div>""", unsafe_allow_html=True)
        return

    existing = st.session_state.find_advice
    btn_label = "🔄 Refresh Advice" if existing else "✨ Get Personalized Advice"
    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        run = st.button(btn_label, type="primary", key="find_get_advice", use_container_width=True)
    with col_hint:
        st.caption("AI will connect your nutrient gaps to specific nearby resources.")

    if run:
        with st.spinner("🧠 Generating personalized recommendations..."):
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
            st.markdown(f"""
            <div style="background:#E8F5E9;border-left:4px solid #66BB6A;
                        border-radius:0 12px 12px 0;padding:0.85rem 1.2rem;
                        color:#1B5E20;font-size:0.9rem;margin-bottom:0.75rem;
                        line-height:1.55;">
                {advice["summary"]}
            </div>""", unsafe_allow_html=True)

        for tip in advice.get("tips", []):
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:flex-start;
                        padding:0.55rem 0.9rem;background:white;
                        border-radius:9px;margin-bottom:6px;
                        box-shadow:0 1px 5px rgba(0,0,0,0.06);
                        border:1px solid #E8F5E9;line-height:1.5;">
                <span style="color:#43A047;font-weight:800;flex-shrink:0;">→</span>
                <span style="font-size:0.88rem;color:#333;">{tip}</span>
            </div>""", unsafe_allow_html=True)

        st.caption(
            "*Advice is AI-generated for informational purposes. "
            "Verify hours and eligibility directly with each resource.*"
        )


def render_find_tab():
    """Main entry point for the Find Free Food Near You tab."""
    st.markdown("""
    <div style="margin-bottom:0.75rem;">
        <div style="font-size:1.25rem;font-weight:800;color:#1B5E20;">
            📍 Find Free Food Near You
        </div>
        <div style="font-size:0.85rem;color:#666;margin-top:2px;">
            Find nearby food banks, pantries, free meals, and SNAP/WIC benefits.
            We'll also show which nutrients you may be missing and where to get them free.
        </div>
    </div>""", unsafe_allow_html=True)

    _init_session_state()

    # ── Search bar ────────────────────────────────────────────────────────────
    zip_code, type_choice, search = _render_search_bar()

    if search and zip_code:
        if len(zip_code) != 5 or not zip_code.isdigit():
            st.error("Please enter a valid 5-digit zip code.")
        else:
            resource_type = _RESOURCE_TYPE_OPTIONS[type_choice]
            with st.spinner("🔎 Finding resources near you..."):
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
        st.markdown("""
        <div style="background:#F9FDF9;border:1px dashed #C8E6C9;border-radius:14px;
                    padding:2rem;color:#888;text-align:center;font-size:0.88rem;">
            <div style="font-size:2.5rem;margin-bottom:0.5rem;">📍</div>
            <strong>Enter a zip code above</strong> and click Search to see free food
            resources available near you.<br>
            <span style="font-size:0.8rem;margin-top:4px;display:block;">
                Try <strong>47906</strong> (West Lafayette) or <strong>47901</strong> (Lafayette) for the demo.
            </span>
        </div>""", unsafe_allow_html=True)
    else:
        _render_resource_list(resources)

        if resources:
            st.divider()
            _render_llm_advice(gaps, resources)
