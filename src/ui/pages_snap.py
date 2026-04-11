"""Snap Food tab — photograph a meal, identify items, get nutrition & analysis."""

import os

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.nutrition.fda_guidelines import compute_dv_percentages
from src.nutrition.models import HealthProfile, NutritionData
from src.ui.components import nutrition_editor
from src.ui.pages_results import results_display
from src.vision.food_identifier import aggregate_nutrition, identify_food

load_dotenv()


def _init_session_state():
    if "snap_identified_foods" not in st.session_state:
        st.session_state.snap_identified_foods = []   # list[dict] with name, estimated_grams
    if "snap_nutrition" not in st.session_state:
        st.session_state.snap_nutrition = None
    if "snap_result" not in st.session_state:
        st.session_state.snap_result = None
    if "snap_dv" not in st.session_state:
        st.session_state.snap_dv = {}
    if "snap_file_key" not in st.session_state:
        st.session_state.snap_file_key = None


def _build_nutrition_from_foods(foods: list[dict]) -> NutritionData:
    """Look up each food via USDA/OFF and aggregate into one NutritionData.

    aggregate_nutrition emits an st.warning listing any foods that
    couldn't be found, and returns an empty NutritionData when nothing
    could be looked up (so the user still gets an editable form).
    """
    api_key = os.getenv("USDA_API_KEY", "")
    return aggregate_nutrition(foods, api_key)


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
        st.session_state.snap_dv = dv
        return

    result = client.analyze(nutrition_data, health_profile, dv)
    st.session_state.snap_result = result
    st.session_state.snap_dv = dv
    st.rerun()


def render_snap_tab():
    """Main entry point for the Snap Food tab."""
    st.header("Snap Food")
    st.caption(
        "Take or upload a photo of your meal — AI will identify the foods and "
        "estimate portions so you can get a full nutrition breakdown."
    )

    _init_session_state()

    # ── Step 1: Photo input ───────────────────────────────────────────────────
    col_upload, col_cam = st.columns(2)
    with col_upload:
        uploaded = st.file_uploader(
            "Upload a food photo",
            type=["jpg", "jpeg", "png"],
            key="snap_file_upload",
        )
    with col_cam:
        camera = st.camera_input("Or take a photo", key="snap_camera")

    photo = uploaded or camera

    if photo is not None:
        file_key = f"{photo.name}_{photo.size}" if hasattr(photo, "name") else str(photo.size)
        col_photo, col_id = st.columns([1, 1])

        with col_photo:
            st.image(Image.open(photo), caption="Your Food", use_container_width=True)

        with col_id:
            # Only identify when a new photo is uploaded
            if st.session_state.snap_file_key != file_key:
                if st.button("Identify Food", type="primary", key="snap_identify_btn"):
                    st.session_state.snap_file_key = file_key
                    st.session_state.snap_result = None
                    st.session_state.snap_nutrition = None
                    st.session_state.snap_dv = {}
                    with st.spinner("Identifying food items..."):
                        foods = identify_food(photo.getvalue())
                    if foods:
                        st.session_state.snap_identified_foods = foods
                        st.rerun()
                    else:
                        st.info(
                            "No foods identified in this photo. "
                            "Try a clearer image or add foods manually below."
                        )
                        st.session_state.snap_identified_foods = []
            else:
                st.success(f"Identified {len(st.session_state.snap_identified_foods)} item(s).")

    # ── Step 2: Editable food table ───────────────────────────────────────────
    st.divider()
    st.subheader("Identified Foods")
    st.caption("Correct names or portions as needed, then click Get Nutrition & Analyze.")

    # Allow manual add even if vision isn't available yet
    with st.expander("Add a food item manually"):
        man_col1, man_col2, man_col3 = st.columns([3, 2, 1])
        with man_col1:
            manual_name = st.text_input("Food name", key="snap_manual_name")
        with man_col2:
            manual_grams = st.number_input(
                "Estimated grams", min_value=1, value=100, key="snap_manual_grams"
            )
        with man_col3:
            st.write("")  # vertical alignment spacer
            st.write("")
            if st.button("Add", key="snap_add_manual") and manual_name:
                st.session_state.snap_identified_foods.append(
                    {"name": manual_name, "estimated_grams": manual_grams, "confidence": "manual"}
                )
                st.rerun()

    foods = st.session_state.snap_identified_foods

    if not foods:
        st.info("No foods identified yet. Use 'Identify Food' or add manually above.")
    else:
        # Render editable rows
        updated_foods = []
        for i, food in enumerate(foods):
            col_name, col_grams, col_conf, col_del = st.columns([3, 2, 2, 1])
            with col_name:
                new_name = st.text_input(
                    "Food", value=food["name"], key=f"snap_name_{i}", label_visibility="collapsed"
                )
            with col_grams:
                new_grams = st.number_input(
                    "Grams", min_value=1,
                    value=int(food.get("estimated_grams") or 100),
                    key=f"snap_grams_{i}", label_visibility="collapsed"
                )
            with col_conf:
                conf = food.get("confidence", "")
                if conf and conf != "manual":
                    st.caption(f"Confidence: {conf}")
                else:
                    st.caption("manual")
            with col_del:
                if st.button("✕", key=f"snap_del_{i}"):
                    st.session_state.snap_identified_foods.pop(i)
                    st.rerun()
            updated_foods.append({"name": new_name, "estimated_grams": new_grams, "confidence": conf})

        # Persist any inline edits
        st.session_state.snap_identified_foods = updated_foods

        st.caption("*Portions are AI-estimated — adjust if needed for accuracy.*")

        # ── Step 3: Get Nutrition & Analyze ──────────────────────────────────
        if st.button("Get Nutrition & Analyze", type="primary", key="snap_analyze_btn"):
            with st.spinner("Looking up nutrition data..."):
                aggregated = _build_nutrition_from_foods(updated_foods)
            st.session_state.snap_nutrition = aggregated
            st.session_state.snap_result = None
            st.rerun()

    # ── Step 4: Review nutrition + analyze ───────────────────────────────────
    if st.session_state.snap_nutrition is not None:
        st.divider()
        st.subheader("Review & Correct Nutrition Data")
        confirmed = nutrition_editor(
            st.session_state.snap_nutrition, key_prefix="snap"
        )
        if confirmed is not st.session_state.snap_nutrition:
            st.session_state.snap_nutrition = confirmed
            with st.spinner("Analyzing..."):
                _run_analysis(confirmed)

    if st.session_state.snap_result is not None:
        st.divider()
        results_display(st.session_state.snap_result, st.session_state.snap_dv)
    elif st.session_state.snap_dv:
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
                for k, v in st.session_state.snap_dv.items()
            ])
            .set_index("Nutrient")
        )
        st.bar_chart(df, color="#4CAF50")
