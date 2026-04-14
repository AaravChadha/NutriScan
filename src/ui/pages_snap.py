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

# ── Food emoji dictionary ─────────────────────────────────────────────────────
_FOOD_EMOJI_MAP: dict[str, str] = {
    # Proteins
    "chicken": "🍗", "beef": "🥩", "steak": "🥩", "fish": "🐟",
    "salmon": "🐟", "tuna": "🐟", "shrimp": "🍤", "pork": "🥩",
    "turkey": "🦃", "lamb": "🥩", "egg": "🥚", "eggs": "🥚",
    "tofu": "🫘", "tempeh": "🫘",
    # Vegetables
    "salad": "🥗", "spinach": "🥬", "broccoli": "🥦", "carrot": "🥕",
    "carrots": "🥕", "tomato": "🍅", "potato": "🥔", "sweet potato": "🍠",
    "corn": "🌽", "onion": "🧅", "garlic": "🧄", "pepper": "🫑",
    "avocado": "🥑", "cucumber": "🥒", "lettuce": "🥬", "mushroom": "🍄",
    "kale": "🥬", "celery": "🥬", "zucchini": "🥒", "eggplant": "🍆",
    # Fruits
    "apple": "🍎", "banana": "🍌", "orange": "🍊", "grape": "🍇",
    "strawberry": "🍓", "lemon": "🍋", "watermelon": "🍉",
    "pineapple": "🍍", "mango": "🥭", "peach": "🍑", "cherry": "🍒",
    "blueberry": "🫐", "raspberry": "🍓", "melon": "🍈",
    # Grains & carbs
    "bread": "🍞", "toast": "🍞", "rice": "🍚", "pasta": "🍝",
    "noodle": "🍜", "noodles": "🍜", "pizza": "🍕", "sandwich": "🥪",
    "wrap": "🌯", "bagel": "🥯", "tortilla": "🌮", "cereal": "🥣",
    "oat": "🥣", "oatmeal": "🥣", "cracker": "🍘", "waffle": "🧇",
    "pancake": "🥞", "muffin": "🧁",
    # Dairy
    "milk": "🥛", "cheese": "🧀", "yogurt": "🫙", "butter": "🧈",
    "cream": "🥛", "ice cream": "🍦",
    # Beverages
    "juice": "🧃", "coffee": "☕", "tea": "🍵", "water": "💧",
    "smoothie": "🥤", "soda": "🥤",
    # Fast food
    "burger": "🍔", "hot dog": "🌭", "taco": "🌮", "fries": "🍟",
    "sushi": "🍱", "soup": "🍜", "ramen": "🍜",
    # Snacks
    "chips": "🍿", "cookie": "🍪", "chocolate": "🍫", "donut": "🍩",
    "cake": "🎂", "candy": "🍬",
    # Legumes
    "bean": "🫘", "beans": "🫘", "lentil": "🫘", "lentils": "🫘",
    "chickpea": "🫘", "peanut": "🥜", "almond": "🌰", "nut": "🥜",
    "nuts": "🥜", "walnut": "🌰",
    # Other
    "salsa": "🍅", "hummus": "🫘", "dip": "🥣",
}


def food_emoji(name: str) -> str:
    """Return a fitting emoji for a food name, or the plate fallback."""
    lower = name.lower()
    # Longest-match wins so "sweet potato" beats "potato"
    matches = [(kw, em) for kw, em in _FOOD_EMOJI_MAP.items() if kw in lower]
    if matches:
        return max(matches, key=lambda x: len(x[0]))[1]
    return "🍽️"


def _init_session_state():
    if "snap_identified_foods" not in st.session_state:
        st.session_state.snap_identified_foods = []
    if "snap_nutrition" not in st.session_state:
        st.session_state.snap_nutrition = None
    if "snap_result" not in st.session_state:
        st.session_state.snap_result = None
    if "snap_dv" not in st.session_state:
        st.session_state.snap_dv = {}
    if "snap_file_key" not in st.session_state:
        st.session_state.snap_file_key = None


def _build_nutrition_from_foods(foods: list[dict]) -> NutritionData:
    api_key = os.getenv("USDA_API_KEY", "")
    return aggregate_nutrition(foods, api_key)


def _run_analysis(nutrition_data: NutritionData) -> None:
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


def _step(num: int, label: str, sub: str = "") -> None:
    sub_html = (
        f'<span style="font-weight:400;color:#555;font-size:0.8rem;"> — {sub}</span>'
        if sub else ""
    )
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


def _conf_pill(conf: str) -> str:
    cfg = {
        "high":   ("#E8F5E9", "#1B5E20", "High ✓"),
        "medium": ("#FFF8E1", "#E65100", "Medium"),
        "low":    ("#FFEBEE", "#B71C1C", "Low"),
        "manual": ("#E3F2FD", "#1565C0", "Manual"),
    }
    bg, color, label = cfg.get((conf or "").lower(), ("#F5F5F5", "#555", conf or "—"))
    return (
        f'<span style="background:{bg};color:{color};padding:2px 9px;'
        f'border-radius:100px;font-size:0.72rem;font-weight:700;">{label}</span>'
    )


def _render_food_table(foods: list[dict]) -> list[dict]:
    """Render an editable food-item table. Returns the (possibly updated) foods list."""
    # Column headers
    st.markdown("""
    <div style="display:grid;grid-template-columns:0.5fr 3fr 2fr 1.5fr 0.5fr;
                gap:6px;padding:5px 10px 5px 6px;background:#F0F7F0;
                border-radius:8px 8px 0 0;margin-bottom:1px;">
        <div style="font-size:0.7rem;font-weight:700;color:#2E7D32;
                    letter-spacing:0.5px;text-transform:uppercase;"></div>
        <div style="font-size:0.7rem;font-weight:700;color:#2E7D32;
                    letter-spacing:0.5px;text-transform:uppercase;">Food</div>
        <div style="font-size:0.7rem;font-weight:700;color:#2E7D32;
                    letter-spacing:0.5px;text-transform:uppercase;">Grams</div>
        <div style="font-size:0.7rem;font-weight:700;color:#2E7D32;
                    letter-spacing:0.5px;text-transform:uppercase;">Confidence</div>
        <div></div>
    </div>""", unsafe_allow_html=True)

    updated_foods = []
    for i, food in enumerate(foods):
        col_ico, col_name, col_grams, col_conf, col_del = st.columns([0.5, 3, 2, 1.5, 0.5])
        with col_ico:
            st.markdown(
                f'<div style="font-size:1.4rem;padding:4px 0;text-align:center;">'
                f'{food_emoji(food["name"])}</div>',
                unsafe_allow_html=True,
            )
        with col_name:
            new_name = st.text_input(
                "Food", value=food["name"], key=f"snap_name_{i}",
                label_visibility="collapsed",
            )
        with col_grams:
            new_grams = st.number_input(
                "g", min_value=1,
                value=int(food.get("estimated_grams") or 100),
                key=f"snap_grams_{i}",
                label_visibility="collapsed",
            )
        with col_conf:
            st.markdown(
                f'<div style="padding-top:6px;">{_conf_pill(food.get("confidence", ""))}</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("✕", key=f"snap_del_{i}", help="Remove"):
                st.session_state.snap_identified_foods.pop(i)
                st.rerun()
        updated_foods.append({
            "name": new_name,
            "estimated_grams": new_grams,
            "confidence": food.get("confidence", ""),
        })
    return updated_foods


def render_snap_tab():
    """Main entry point for the Snap Food tab."""
    st.markdown("""
    <div style="margin-bottom:0.5rem;">
        <div style="font-size:1.25rem;font-weight:800;color:#1B5E20;">🍔 Snap Food</div>
        <div style="font-size:0.85rem;color:#666;margin-top:2px;">
            Photograph your meal — AI identifies each food and estimates portions
            for a full nutrition breakdown.
        </div>
    </div>""", unsafe_allow_html=True)

    _init_session_state()

    # ── Step 1: Photo input ───────────────────────────────────────────────────
    _step(1, "Upload or take a food photo")

    col_upload, col_camera = st.columns(2)
    with col_upload:
        uploaded = st.file_uploader(
            "Upload",
            type=["jpg", "jpeg", "png", "heic", "heif", "webp"],
            key="snap_file_upload",
            label_visibility="collapsed",
        )
    with col_camera:
        camera = st.camera_input("Camera", key="snap_camera", label_visibility="collapsed")

    photo = uploaded or camera

    if photo is not None:
        file_key = f"{photo.name}_{photo.size}" if hasattr(photo, "name") else str(photo.size)

        col_img, col_action = st.columns([1.6, 1])
        with col_img:
            st.image(Image.open(photo), caption="Your meal", use_container_width=True)
        with col_action:
            if st.session_state.snap_file_key != file_key:
                st.markdown("""
                <div style="background:#F9FDF9;border:1px solid #C8E6C9;
                            border-radius:12px;padding:1rem;margin-top:0.5rem;">
                    <div style="font-weight:700;color:#1B5E20;font-size:0.9rem;
                                margin-bottom:4px;">📸 Photo ready</div>
                    <div style="font-size:0.8rem;color:#666;line-height:1.5;">
                        Click <strong>Identify Food</strong> to detect items
                        and estimate portions automatically.
                    </div>
                </div>""", unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button(
                    "🔍 Identify Food", type="primary",
                    key="snap_identify_btn", use_container_width=True,
                ):
                    st.session_state.snap_file_key = file_key
                    st.session_state.snap_result = None
                    st.session_state.snap_nutrition = None
                    st.session_state.snap_dv = {}
                    with st.spinner("🧠 Identifying food items..."):
                        foods = identify_food(photo.getvalue())
                    if foods:
                        st.session_state.snap_identified_foods = foods
                        st.rerun()
                    else:
                        st.info("No foods identified. Try a clearer photo or add items manually.")
                        st.session_state.snap_identified_foods = []
            else:
                n = len(st.session_state.snap_identified_foods)
                st.markdown(f"""
                <div style="background:#E8F5E9;border:1px solid #66BB6A;
                            border-radius:12px;padding:0.9rem 1rem;
                            margin-top:0.5rem;text-align:center;">
                    <div style="font-size:1.6rem;">✅</div>
                    <div style="font-weight:700;color:#1B5E20;font-size:0.9rem;">
                        {n} item{"s" if n != 1 else ""} identified
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── Step 2: Editable food table ───────────────────────────────────────────
    st.divider()
    _step(2, "Review identified foods", "Adjust names or gram weights as needed")

    with st.expander("➕ Add a food item manually", expanded=False):
        mc1, mc2, mc3 = st.columns([3, 2, 1])
        with mc1:
            manual_name = st.text_input(
                "Food name", key="snap_manual_name",
                placeholder="e.g. Grilled chicken breast",
            )
        with mc2:
            manual_grams = st.number_input(
                "Grams", min_value=1, value=100, key="snap_manual_grams",
            )
        with mc3:
            st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
            if st.button("Add", key="snap_add_manual", type="primary") and manual_name:
                st.session_state.snap_identified_foods.append(
                    {"name": manual_name, "estimated_grams": manual_grams, "confidence": "manual"}
                )
                st.rerun()

    foods = st.session_state.snap_identified_foods

    if not foods:
        st.markdown("""
        <div style="background:#F9FDF9;border:1px dashed #C8E6C9;border-radius:12px;
                    padding:1.25rem;color:#888;text-align:center;font-size:0.87rem;">
            No foods identified yet. Use <strong>Identify Food</strong> above
            or add items manually.
        </div>""", unsafe_allow_html=True)
    else:
        updated_foods = _render_food_table(foods)
        st.session_state.snap_identified_foods = updated_foods

        # Estimated calorie total banner
        total_g = sum(f.get("estimated_grams") or 0 for f in updated_foods)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    background:#F9FDF9;border:1px solid #C8E6C9;border-radius:0 0 8px 8px;
                    padding:6px 12px;margin-top:1px;margin-bottom:2px;">
            <span style="font-size:0.8rem;color:#6A8A6A;font-style:italic;">
                ⚡ Portions are AI-estimated — adjust if needed for accuracy.
            </span>
            <span style="font-size:0.8rem;font-weight:700;color:#2E7D32;">
                {len(updated_foods)} item{"s" if len(updated_foods) != 1 else ""}
                &nbsp;·&nbsp; ~{total_g} g total
            </span>
        </div>""", unsafe_allow_html=True)

        # ── Step 3: Analyze ──────────────────────────────────────────────────
        _step(3, "Get full nutrition breakdown & AI analysis")
        if st.button(
            "📊 Get Nutrition & Analyze", type="primary",
            key="snap_analyze_btn", use_container_width=True,
        ):
            with st.spinner("🔎 Looking up nutrition data..."):
                aggregated = _build_nutrition_from_foods(updated_foods)
            st.session_state.snap_nutrition = aggregated
            st.session_state.snap_result = None
            st.rerun()

    # ── Step 4: Review + run analysis ────────────────────────────────────────
    if st.session_state.snap_nutrition is not None:
        st.divider()
        _step(4, "Review & correct nutrition data", "Edit values then confirm to analyze")
        confirmed = nutrition_editor(st.session_state.snap_nutrition, key_prefix="snap")
        if confirmed is not st.session_state.snap_nutrition:
            st.session_state.snap_nutrition = confirmed
            with st.spinner("🧠 Analyzing..."):
                _run_analysis(confirmed)

    if st.session_state.snap_result is not None:
        st.divider()
        results_display(st.session_state.snap_result, st.session_state.snap_dv)
    elif st.session_state.snap_dv:
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
                for k, v in st.session_state.snap_dv.items()
            ])
            .set_index("Nutrient")
        )
        st.bar_chart(df, color="#4CAF50")
