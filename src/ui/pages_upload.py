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
    if "upload_confidence" not in st.session_state:
        st.session_state.upload_confidence = None
    if "upload_fields_parsed" not in st.session_state:
        st.session_state.upload_fields_parsed = 0
    if "upload_source" not in st.session_state:
        st.session_state.upload_source = "ocr"
    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None
    if "upload_dv" not in st.session_state:
        st.session_state.upload_dv = {}


def _confidence_label(score: float) -> str:
    """Map a 0.0-1.0 confidence score to our low/medium/high bucket."""
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _read_label(uploaded_file) -> tuple[NutritionData, str, str, int, str]:
    """Read a nutrition label from the uploaded file.

    Vision-first: tries Groq's vision model, which handles poor phone
    photos much better than Tesseract + regex. Falls back to Tesseract if
    GROQ_API_KEY is unset, the API fails, or the response can't be parsed.

    Returns (NutritionData, raw_text, confidence, fields_parsed, source)
    where `source` is 'vision' or 'ocr' so the UI can tell the user which
    path was used.
    """
    # --- Vision path ---
    try:
        from src.vision.label_reader import extract_label_with_vision

        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        vision_result = extract_label_with_vision(image_bytes)
        if vision_result is not None and vision_result.fields_parsed > 0:
            return (
                vision_result.nutrition,
                vision_result.raw_json,
                _confidence_label(vision_result.confidence),
                vision_result.fields_parsed,
                "vision",
            )
    except Exception as e:
        # Don't surface — we still have the Tesseract fallback
        st.info(f"Vision reader unavailable ({e}); falling back to OCR.")

    # --- Tesseract fallback ---
    try:
        from src.ocr.extractor import extract

        uploaded_file.seek(0)
        image = Image.open(uploaded_file).convert("RGB")
        ocr_result = extract(image)
        uploaded_file.seek(0)
        return (
            ocr_result.nutrition,
            ocr_result.raw_text,
            ocr_result.confidence,
            ocr_result.fields_parsed,
            "ocr",
        )
    except Exception as e:
        st.error(f"Label reading failed: {e}")
        return NutritionData(), "", "low", 0, "ocr"


def _run_analysis(nutrition_data: NutritionData) -> None:
    """Compute DV% and call LLM analyze(). Stores results in session_state."""
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


def _step(num: int, label: str, sub: str = "") -> None:
    sub_html = f'<span style="font-weight:400;color:#555;font-size:0.8rem;"> — {sub}</span>' if sub else ""
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:8px 14px;
                background:linear-gradient(90deg,#E8F5E9,transparent);
                border-left:4px solid #2E7D32;border-radius:0 9px 9px 0;
                margin:1rem 0 0.5rem;">
        <div style="width:26px;height:26px;background:#2E7D32;color:white;
                    border-radius:50%;display:flex;align-items:center;
                    justify-content:center;font-size:12px;font-weight:800;
                    flex-shrink:0;">{num}</div>
        <span style="font-weight:700;font-size:0.9rem;color:#1B5E20;">{label}</span>{sub_html}
    </div>""", unsafe_allow_html=True)


def render_upload_tab():
    """Main entry point for the Upload Label tab."""
    st.markdown("""
    <div style="margin-bottom:0.5rem;">
        <div style="font-size:1.25rem;font-weight:800;color:#1B5E20;">📷 Upload Nutrition Label</div>
        <div style="font-size:0.85rem;color:#666;margin-top:2px;">
            Upload a photo of any nutrition label — AI will extract all values automatically.
        </div>
    </div>""", unsafe_allow_html=True)

    _init_session_state()

    _step(1, "Upload your label photo", "JPG, PNG, HEIC, WEBP supported")

    uploaded = st.file_uploader(
        "Choose a label image",
        type=["jpg", "jpeg", "png", "heic", "heif", "webp"],
        key="upload_label_file",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        # Auto-run reading only when a new file is uploaded
        file_key = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.upload_file_key != file_key:
            st.session_state.upload_file_key = file_key
            st.session_state.upload_result = None
            st.session_state.upload_dv = {}
            with st.spinner("🔍 Reading label with AI..."):
                nutrition, raw_text, confidence, fields_parsed, source = _read_label(uploaded)
                st.session_state.upload_nutrition = nutrition
                st.session_state.upload_raw_text = raw_text
                st.session_state.upload_confidence = confidence
                st.session_state.upload_fields_parsed = fields_parsed
                st.session_state.upload_source = source

        # Confidence feedback
        source_label = "AI Vision" if st.session_state.upload_source == "vision" else "OCR"
        fields = st.session_state.upload_fields_parsed
        conf = st.session_state.upload_confidence

        if conf == "low":
            st.warning(
                f"**{source_label}** could only read {fields} field(s) clearly. "
                "Please review the values below carefully, or switch to **Manual Entry**."
            )
        elif conf == "medium":
            st.info(f"**{source_label}** parsed {fields} of ~15 fields. Review before analyzing.")
        else:
            st.success(f"**{source_label}** read {fields} fields cleanly. ✓")

        col_img, col_ocr = st.columns([1, 1])
        with col_img:
            image = Image.open(uploaded)
            st.image(image, caption="Uploaded Label", use_container_width=True)
        with col_ocr:
            if st.session_state.upload_raw_text:
                label_txt = (
                    "Raw AI response (JSON)"
                    if st.session_state.upload_source == "vision"
                    else "Raw OCR text"
                )
                with st.expander(f"🔎 {label_txt}"):
                    st.text(st.session_state.upload_raw_text)
            else:
                st.markdown("""
                <div style="background:#F9FDF9;border:1px dashed #C8E6C9;border-radius:10px;
                            padding:1rem;color:#888;font-size:0.84rem;text-align:center;
                            margin-top:0.5rem;">
                    Extracted data will appear here after scanning.
                </div>""", unsafe_allow_html=True)

    if st.session_state.upload_nutrition is not None:
        st.divider()
        _step(2, "Review & correct extracted values", "Edit anything that looks wrong")
        confirmed = nutrition_editor(
            st.session_state.upload_nutrition, key_prefix="upload"
        )
        if confirmed is not st.session_state.upload_nutrition:
            st.session_state.upload_nutrition = confirmed
            with st.spinner("🧠 Analyzing nutrition..."):
                _run_analysis(confirmed)

    if st.session_state.upload_result is not None:
        st.divider()
        _step(3, "Your analysis is ready")
        results_display(st.session_state.upload_result, st.session_state.upload_dv)
    elif st.session_state.upload_dv:
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
                for k, v in st.session_state.upload_dv.items()
            ])
            .set_index("Nutrient")
        )
        st.bar_chart(df, color="#4CAF50")
