"""Upload Label tab — upload a nutrition label image, OCR it, then analyze."""

import streamlit as st
from PIL import Image

from src.nutrition.fda_guidelines import compute_dv_percentages
from src.nutrition.models import HealthProfile, NutritionData
from src.ui.components import nutrition_editor
from src.ui.pages_results import results_display


def _init_session_state():
    if "upload_file_key" not in st.session_state:
        st.session_state.upload_file_key = None
    if "upload_nutrition" not in st.session_state:
        st.session_state.upload_nutrition = None
    if "upload_raw_text" not in st.session_state:
        st.session_state.upload_raw_text = ""
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None
    if "upload_dv" not in st.session_state:
        st.session_state.upload_dv = {}


def _run_ocr(uploaded_file) -> tuple[NutritionData, str]:
    """Run OCR on the uploaded file. Returns (NutritionData, raw_text)."""
    try:
        from src.ocr.extractor import extract_nutrition
        return extract_nutrition(uploaded_file)
    except ImportError:
        # OCR pipeline not built yet (Neil's 3.1)
        return NutritionData(), ""


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
        st.session_state.upload_dv = dv
        return

    result = client.analyze(nutrition_data, health_profile, dv)
    st.session_state.upload_result = result
    st.session_state.upload_dv = dv
    st.rerun()


def render_upload_tab():
    """Main entry point for the Upload Label tab."""
    st.header("Upload Nutrition Label")
    st.caption("Upload a photo of a nutrition label to scan and analyze it.")

    _init_session_state()

    uploaded = st.file_uploader(
        "Choose a label image",
        type=["jpg", "jpeg", "png"],
        key="upload_label_file",
    )

    if uploaded is not None:
        # Auto-run OCR only when a new file is uploaded
        file_key = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.upload_file_key != file_key:
            st.session_state.upload_file_key = file_key
            st.session_state.upload_result = None
            st.session_state.upload_dv = {}
            with st.spinner("Scanning label..."):
                nutrition, raw_text = _run_ocr(uploaded)
                st.session_state.upload_nutrition = nutrition
                st.session_state.upload_raw_text = raw_text
                if not raw_text:
                    st.info(
                        "OCR pipeline not ready yet (waiting on Neil's 3.1). "
                        "You can still fill in the nutrition data manually below."
                    )

        col_img, col_ocr = st.columns([1, 1])

        with col_img:
            image = Image.open(uploaded)
            st.image(image, caption="Uploaded Label", use_container_width=True)

        with col_ocr:
            if st.session_state.upload_raw_text:
                with st.expander("Raw OCR Text"):
                    st.text(st.session_state.upload_raw_text)
            else:
                st.caption("Raw OCR text will appear here after scanning.")

    if st.session_state.upload_nutrition is not None:
        st.divider()
        st.subheader("Review & Correct Nutrition Data")
        st.caption("Edit any values the scanner may have missed, then click Confirm & Analyze.")

        confirmed = nutrition_editor(
            st.session_state.upload_nutrition, key_prefix="upload"
        )

        # nutrition_editor returns a new object on form submit
        if confirmed is not st.session_state.upload_nutrition:
            st.session_state.upload_nutrition = confirmed
            with st.spinner("Analyzing..."):
                _run_analysis(confirmed)

    if st.session_state.upload_result is not None:
        st.divider()
        results_display(st.session_state.upload_result, st.session_state.upload_dv)
    elif st.session_state.upload_dv:
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
                for k, v in st.session_state.upload_dv.items()
            ])
            .set_index("Nutrient")
        )
        st.bar_chart(df, color="#4CAF50")
