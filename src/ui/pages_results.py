"""Results display page — shows LLM analysis output and DV% breakdown."""

import pandas as pd
import streamlit as st

from src.nutrition.models import AnalysisResult

# Risk level → (color label, Streamlit status method)
_RISK_CONFIG = {
    "low":     ("🟢 Low Risk",     st.success),
    "moderate":("🟡 Moderate Risk", st.warning),
    "high":    ("🔴 High Risk",     st.error),
}


def results_display(result: AnalysisResult, dv_percentages: dict) -> None:
    """
    Render the full analysis results.

    Args:
        result: AnalysisResult from the LLM pipeline.
        dv_percentages: dict from compute_dv_percentages().
    """
    st.header("Analysis Results")

    # ── Overall Risk ─────────────────────────────────────────────────────────
    risk_key = result.overall_risk.lower()
    label, alert_fn = _RISK_CONFIG.get(risk_key, ("⚪ Unknown", st.info))
    alert_fn(f"**Overall Risk: {label}**")

    # ── Summary ───────────────────────────────────────────────────────────────
    if result.summary:
        st.markdown(f"> {result.summary}")

    st.divider()

    # ── Flags ─────────────────────────────────────────────────────────────────
    col_flags, col_recs = st.columns([1, 1])

    with col_flags:
        st.subheader("Flags")

        if result.allergen_flags:
            for flag in result.allergen_flags:
                st.error(f"🚨 **Allergen:** {flag}")
        
        if result.preservative_flags:
            for flag in result.preservative_flags:
                st.warning(f"⚠️ **Preservative:** {flag}")

        if result.nutrient_flags:
            for flag in result.nutrient_flags:
                # High nutrient flags are warnings; positive ones are green
                lower = flag.lower()
                if any(w in lower for w in ["high", "excess", "too much", "low"]):
                    st.warning(f"📊 {flag}")
                else:
                    st.success(f"✅ {flag}")

        if not any([result.allergen_flags, result.preservative_flags, result.nutrient_flags]):
            st.success("✅ No flags detected.")

    # ── Goal Alignment ────────────────────────────────────────────────────────
    with col_recs:
        st.subheader("Goal Alignment")
        if result.goal_alignment:
            for item in result.goal_alignment:
                lower = item.lower()
                if any(w in lower for w in ["not", "exceeds", "mismatch", "conflict", "avoid"]):
                    st.warning(f"⚠️ {item}")
                else:
                    st.success(f"✅ {item}")
        else:
            st.info("No health profile set — add one in the sidebar for personalized alignment.")

    st.divider()

    # ── Recommendations ───────────────────────────────────────────────────────
    if result.recommendations:
        st.subheader("Recommendations")
        for rec in result.recommendations:
            st.markdown(f"- {rec}")

    st.divider()

    # ── DV% Bar Chart ─────────────────────────────────────────────────────────
    if dv_percentages:
        st.subheader("% Daily Value Breakdown")

        labels = {
            "calories": "Calories",
            "total_fat": "Total Fat",
            "saturated_fat": "Saturated Fat",
            "cholesterol": "Cholesterol",
            "sodium": "Sodium",
            "total_carbs": "Total Carbs",
            "dietary_fiber": "Dietary Fiber",
            "added_sugars": "Added Sugars",
            "protein": "Protein",
            "vitamin_d": "Vitamin D",
            "calcium": "Calcium",
            "iron": "Iron",
            "potassium": "Potassium",
        }

        df = pd.DataFrame([
            {"Nutrient": labels.get(k, k.replace("_", " ").title()), "% Daily Value": v}
            for k, v in dv_percentages.items()
        ]).set_index("Nutrient")

        st.bar_chart(df, color="#4CAF50")

        # Flag anything over 20% DV as high, under 5% as low
        high = [labels.get(k, k) for k, v in dv_percentages.items() if v >= 20]
        low  = [labels.get(k, k) for k, v in dv_percentages.items() if v <= 5 and v > 0]

        if high:
            st.caption(f"⚠️ High (≥20% DV): {', '.join(high)}")
        if low:
            st.caption(f"ℹ️ Low (≤5% DV): {', '.join(low)}")

    st.caption("*Analysis is AI-generated and for informational purposes only. Not medical advice.*")