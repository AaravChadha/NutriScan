"""Results display page — shows LLM analysis output and DV% breakdown."""

import streamlit as st

from src.nutrition.models import AnalysisResult

# Nutrients where high % DV is a concern (limit these)
_BAD_NUTRIENTS = {"sodium", "total_fat", "saturated_fat", "cholesterol", "added_sugars", "trans_fat"}

_DV_LABELS = {
    "calories":      "Calories",
    "total_fat":     "Total Fat",
    "saturated_fat": "Saturated Fat",
    "cholesterol":   "Cholesterol",
    "sodium":        "Sodium",
    "total_carbs":   "Total Carbs",
    "dietary_fiber": "Dietary Fiber",
    "added_sugars":  "Added Sugars",
    "protein":       "Protein",
    "vitamin_d":     "Vitamin D",
    "calcium":       "Calcium",
    "iron":          "Iron",
    "potassium":     "Potassium",
}

# Which bucket each nutrient belongs to for the grouped bar display
_DV_GROUPS = {
    "macros":  ["calories", "total_fat", "saturated_fat", "cholesterol",
                "sodium", "total_carbs", "dietary_fiber", "added_sugars", "protein"],
    "micros":  ["vitamin_d", "calcium", "iron", "potassium"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flag_card(text: str, style: str) -> None:
    """style: 'danger' | 'warn' | 'good' | 'info'"""
    cfg = {
        "danger": ("#FFEBEE", "#EF5350", "#B71C1C"),
        "warn":   ("#FFF8E1", "#FFB300", "#E65100"),
        "good":   ("#E8F5E9", "#66BB6A", "#1B5E20"),
        "info":   ("#E3F2FD", "#42A5F5", "#1565C0"),
    }
    bg, border, color = cfg.get(style, cfg["info"])
    st.markdown(f"""
    <div style="background:{bg};border-left:4px solid {border};
                border-radius:0 9px 9px 0;padding:0.5rem 0.9rem;
                color:{color};font-size:0.87rem;margin-bottom:5px;
                line-height:1.45;">{text}</div>""",
    unsafe_allow_html=True)


def _section_title(icon: str, label: str) -> None:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;
                padding:0.35rem 0;margin:0 0 0.65rem;
                border-bottom:2px solid rgba(46,125,50,0.2);">
        <span style="font-size:1rem;">{icon}</span>
        <span style="font-weight:700;font-size:0.95rem;color:#4CAF50;">{label}</span>
    </div>""", unsafe_allow_html=True)


def _nutrition_grade(overall_risk: str, allergen_count: int, flag_count: int) -> tuple[str, str, str]:
    """Return (grade, bg_color, text_color) based on risk profile."""
    risk = overall_risk.lower()
    if risk == "low" and allergen_count == 0 and flag_count == 0:
        return "A+", "#E8F5E9", "#1B5E20"
    if risk == "low" and allergen_count == 0 and flag_count <= 1:
        return "A",  "#E8F5E9", "#1B5E20"
    if risk == "low" and allergen_count == 0:
        return "B+", "#F1F8E9", "#33691E"
    if risk == "low":
        return "B",  "#F9FBE7", "#558B2F"
    if risk == "moderate" and allergen_count == 0 and flag_count <= 2:
        return "C+", "#FFFDE7", "#F9A825"
    if risk == "moderate" and allergen_count == 0:
        return "C",  "#FFF8E1", "#E65100"
    if risk == "moderate":
        return "D",  "#FBE9E7", "#BF360C"
    if allergen_count == 0:
        return "D",  "#FBE9E7", "#BF360C"
    return "F",  "#FFEBEE", "#B71C1C"


def _render_quick_stats(result: AnalysisResult) -> None:
    """Three at-a-glance metric tiles."""
    allergen_count = len(result.allergen_flags)
    total_flags = allergen_count + len(result.preservative_flags) + len(result.nutrient_flags)
    goals_met  = sum(
        1 for item in result.goal_alignment
        if not any(w in item.lower() for w in ["not", "exceeds", "mismatch", "conflict", "avoid"])
    )
    goals_total = len(result.goal_alignment)

    grade, grade_bg, grade_color = _nutrition_grade(
        result.overall_risk, allergen_count, total_flags
    )

    # Allergen tile
    a_color = "#B71C1C" if allergen_count > 0 else "#1B5E20"
    a_bg    = "#FFEBEE"  if allergen_count > 0 else "#E8F5E9"
    a_border= "#EF5350"  if allergen_count > 0 else "#66BB6A"
    a_label = f"{allergen_count} Allergen{'s' if allergen_count != 1 else ''}"

    # Goals tile
    if goals_total == 0:
        g_display, g_color, g_bg, g_border = "—", "#546E7A", "#ECEFF1", "#90A4AE"
    elif goals_met == goals_total:
        g_display, g_color, g_bg, g_border = f"{goals_met}/{goals_total}", "#1B5E20", "#E8F5E9", "#66BB6A"
    else:
        g_display, g_color, g_bg, g_border = f"{goals_met}/{goals_total}", "#E65100", "#FFF8E1", "#FFB300"

    # Flags tile
    f_color  = "#B71C1C" if total_flags > 3 else "#E65100" if total_flags > 0 else "#1B5E20"
    f_bg     = "#FFEBEE"  if total_flags > 3 else "#FFF8E1" if total_flags > 0 else "#E8F5E9"
    f_border = "#EF5350"  if total_flags > 3 else "#FFB300" if total_flags > 0 else "#66BB6A"

    c1, c2, c3, c4 = st.columns(4)

    # Grade tile
    with c1:
        st.markdown(f"""
        <div style="background:{grade_bg};border:2px solid {grade_color};
                    border-radius:14px;padding:0.85rem 1rem;text-align:center;">
            <div style="font-size:2rem;font-weight:900;color:{grade_color};
                        line-height:1;">{grade}</div>
            <div style="font-size:0.74rem;color:{grade_color};opacity:0.75;
                        margin-top:3px;font-weight:600;">Nutrition Grade</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="background:{a_bg};border:1px solid {a_border};
                    border-radius:14px;padding:0.85rem 1rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:{a_color};
                        line-height:1;">{allergen_count}</div>
            <div style="font-size:0.74rem;color:{a_color};opacity:0.75;
                        margin-top:3px;font-weight:600;">{a_label}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div style="background:{g_bg};border:1px solid {g_border};
                    border-radius:14px;padding:0.85rem 1rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:{g_color};
                        line-height:1;">{g_display}</div>
            <div style="font-size:0.74rem;color:{g_color};opacity:0.75;
                        margin-top:3px;font-weight:600;">Goals Met</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div style="background:{f_bg};border:1px solid {f_border};
                    border-radius:14px;padding:0.85rem 1rem;text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:{f_color};
                        line-height:1;">{total_flags}</div>
            <div style="font-size:0.74rem;color:{f_color};opacity:0.75;
                        margin-top:3px;font-weight:600;">Total Flags</div>
        </div>""", unsafe_allow_html=True)


def _render_dv_bars(dv_percentages: dict) -> None:
    """Render grouped custom HTML/CSS progress bars for % Daily Value."""
    def _bar_row(k: str, v: float) -> str:
        label       = _DV_LABELS.get(k, k.replace("_", " ").title())
        display_pct = min(v, 100)
        if v >= 20:
            color, text_color = ("#EF5350", "#B71C1C") if k in _BAD_NUTRIENTS else ("#43A047", "#1B5E20")
        elif v >= 5:
            color, text_color = "#4CAF50", "#2E7D32"
        elif v > 0:
            color, text_color = "#FFA726", "#E65100"
        else:
            color, text_color = "#BDBDBD", "#9E9E9E"
        return f"""
        <div style="margin:6px 0;">
            <div style="display:flex;justify-content:space-between;
                        font-size:12px;color:inherit;opacity:0.8;margin-bottom:3px;">
                <span>{label}</span>
                <span style="font-weight:700;color:{text_color};">{v}%</span>
            </div>
            <div style="height:9px;background:#EEEEEE;border-radius:5px;overflow:hidden;">
                <div style="height:100%;width:{display_pct}%;
                            background:{color};border-radius:5px;"></div>
            </div>
        </div>"""

    legend = """
    <div style="margin-top:0.8rem;padding-top:0.6rem;border-top:1px solid rgba(46,125,50,0.15);
                display:flex;gap:1.2rem;font-size:11px;color:#777;flex-wrap:wrap;">
        <span><span style="display:inline-block;width:10px;height:10px;
                           background:#EF5350;border-radius:2px;
                           margin-right:4px;vertical-align:middle;"></span>≥20% limit</span>
        <span><span style="display:inline-block;width:10px;height:10px;
                           background:#43A047;border-radius:2px;
                           margin-right:4px;vertical-align:middle;"></span>≥20% beneficial</span>
        <span><span style="display:inline-block;width:10px;height:10px;
                           background:#4CAF50;border-radius:2px;
                           margin-right:4px;vertical-align:middle;"></span>5–20% normal</span>
        <span><span style="display:inline-block;width:10px;height:10px;
                           background:#FFA726;border-radius:2px;
                           margin-right:4px;vertical-align:middle;"></span>1–5% low</span>
    </div>"""

    macro_keys = [k for k in _DV_GROUPS["macros"] if k in dv_percentages]
    micro_keys = [k for k in _DV_GROUPS["micros"] if k in dv_percentages]
    extra_keys = [k for k in dv_percentages if k not in macro_keys and k not in micro_keys]

    # Macros — two-column grid; micros — single row
    macro_bars  = [_bar_row(k, dv_percentages[k]) for k in macro_keys]
    micro_bars  = [_bar_row(k, dv_percentages[k]) for k in micro_keys]
    extra_bars  = [_bar_row(k, dv_percentages[k]) for k in extra_keys]

    half = len(macro_bars) // 2 + len(macro_bars) % 2
    macro_col1_html = "".join(macro_bars[:half])
    macro_col2_html = "".join(macro_bars[half:])
    micro_row_html  = "".join(micro_bars + extra_bars)

    micro_section = ""
    if micro_row_html:
        # Micros in a 2-col grid too
        all_micro = micro_bars + extra_bars
        mhalf = len(all_micro) // 2 + len(all_micro) % 2
        micro_section = f"""
        <div style="margin-top:1rem;padding-top:0.75rem;border-top:1px solid rgba(46,125,50,0.15);">
            <div style="font-size:0.72rem;font-weight:700;color:#4CAF50;
                        letter-spacing:0.8px;text-transform:uppercase;
                        margin-bottom:8px;">🌿 Micronutrients & Minerals</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 2.5rem;">
                <div>{"".join(all_micro[:mhalf])}</div>
                <div>{"".join(all_micro[mhalf:])}</div>
            </div>
        </div>"""

    st.markdown(f"""
    <div style="background:rgba(128,128,128,0.06);border-radius:14px;padding:1.2rem 1.5rem;
                box-shadow:0 2px 10px rgba(0,0,0,0.07);border:1px solid rgba(46,125,50,0.15);">
        <div style="font-size:0.72rem;font-weight:700;color:#4CAF50;
                    letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px;">
            🥩 Macronutrients
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 2.5rem;">
            <div>{macro_col1_html}</div>
            <div>{macro_col2_html}</div>
        </div>
        {micro_section}
        {legend}
    </div>""", unsafe_allow_html=True)


# ── Main display function ─────────────────────────────────────────────────────

def results_display(result: AnalysisResult, dv_percentages: dict) -> None:
    """
    Render the full analysis results.

    Args:
        result: AnalysisResult from the LLM pipeline.
        dv_percentages: dict from compute_dv_percentages().
    """
    st.markdown("""
    <div style="font-size:1.25rem;font-weight:800;color:#4CAF50;
                margin-bottom:0.85rem;">
        📋 Analysis Results
    </div>""", unsafe_allow_html=True)

    # ── Quick stats + grade row ───────────────────────────────────────────────
    _render_quick_stats(result)
    st.markdown("<div style='margin-top:0.85rem;'></div>", unsafe_allow_html=True)

    # ── Overall Risk banner ───────────────────────────────────────────────────
    risk_key = result.overall_risk.lower()
    risk_cfg = {
        "low": {
            "icon": "✅", "label": "Low Risk",
            "color": "#1B5E20", "bg": "#E8F5E9", "border": "#66BB6A",
            "sub": "No major concerns detected",
        },
        "moderate": {
            "icon": "⚠️", "label": "Moderate Risk",
            "color": "#E65100", "bg": "#FFF3E0", "border": "#FFB300",
            "sub": "Some things to watch out for",
        },
        "high": {
            "icon": "🚨", "label": "High Risk",
            "color": "#B71C1C", "bg": "#FFEBEE", "border": "#EF5350",
            "sub": "Multiple concerns detected",
        },
    }.get(risk_key, {
        "icon": "ℹ️", "label": "Unknown", "color": "#546E7A",
        "bg": "#ECEFF1", "border": "#90A4AE", "sub": "Risk level undetermined",
    })

    st.markdown(f"""
    <div style="background:{risk_cfg['bg']};border:2px solid {risk_cfg['border']};
                border-radius:14px;padding:1rem 1.4rem;margin-bottom:0.85rem;
                display:flex;align-items:center;gap:1rem;">
        <div style="font-size:2.2rem;line-height:1;">{risk_cfg['icon']}</div>
        <div>
            <div style="font-size:1.25rem;font-weight:800;color:{risk_cfg['color']};
                        line-height:1.2;">{risk_cfg['label']}</div>
            <div style="color:{risk_cfg['color']};opacity:0.72;font-size:0.84rem;
                        margin-top:2px;">{risk_cfg['sub']}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    if result.summary:
        st.markdown(f"""
        <div style="background:rgba(128,128,128,0.06);border-left:4px solid #66BB6A;
                    border-radius:0 10px 10px 0;padding:0.8rem 1.2rem;
                    color:inherit;font-style:italic;font-size:0.91rem;
                    box-shadow:0 2px 8px rgba(0,0,0,0.05);margin-bottom:1rem;
                    line-height:1.55;">{result.summary}</div>""",
        unsafe_allow_html=True)

    st.divider()

    # ── Flags + Goal Alignment ────────────────────────────────────────────────
    col_flags, col_goals = st.columns(2)

    with col_flags:
        _section_title("🚩", "Flags")
        if result.allergen_flags:
            for flag in result.allergen_flags:
                _flag_card(f"🚨 <strong>Allergen:</strong> {flag}", "danger")
        if result.preservative_flags:
            for flag in result.preservative_flags:
                _flag_card(f"⚠️ <strong>Preservative:</strong> {flag}", "warn")
        if result.nutrient_flags:
            for flag in result.nutrient_flags:
                lower = flag.lower()
                if any(w in lower for w in ["high", "excess", "too much"]):
                    _flag_card(f"📈 {flag}", "warn")
                elif "low" in lower:
                    _flag_card(f"📉 {flag}", "info")
                else:
                    _flag_card(f"✅ {flag}", "good")
        if not any([result.allergen_flags, result.preservative_flags, result.nutrient_flags]):
            _flag_card("✅ No flags detected — looks clean!", "good")

    with col_goals:
        _section_title("🎯", "Goal Alignment")
        if result.goal_alignment:
            for item in result.goal_alignment:
                lower = item.lower()
                if any(w in lower for w in ["not", "exceeds", "mismatch", "conflict", "avoid"]):
                    _flag_card(f"⚠️ {item}", "warn")
                else:
                    _flag_card(f"✅ {item}", "good")
        else:
            st.markdown("""
            <div style="background:rgba(128,128,128,0.06);border:1px dashed #C8E6C9;
                        border-radius:10px;padding:0.75rem 1rem;
                        color:#6A8A6A;font-size:0.85rem;">
                No health profile set — add one in the sidebar for personalized goal tracking.
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Recommendations ───────────────────────────────────────────────────────
    if result.recommendations:
        _section_title("💡", "Recommendations")
        for rec in result.recommendations:
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:flex-start;
                        padding:0.6rem 0.9rem;background:rgba(128,128,128,0.06);
                        border-radius:9px;margin-bottom:6px;
                        box-shadow:0 1px 5px rgba(0,0,0,0.06);
                        border:1px solid rgba(46,125,50,0.15);line-height:1.5;">
                <span style="color:#43A047;font-weight:800;font-size:1rem;
                             flex-shrink:0;margin-top:1px;">→</span>
                <span style="font-size:0.88rem;color:inherit;">{rec}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("")

    st.divider()

    # ── DV% Bar Chart ─────────────────────────────────────────────────────────
    if dv_percentages:
        _section_title("📊", "% Daily Value Breakdown")
        _render_dv_bars(dv_percentages)

    st.caption("*Analysis is AI-generated and for informational purposes only. Not medical advice.*")
