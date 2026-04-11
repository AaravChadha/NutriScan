"""Recipe Generator tab — build a pantry and generate nutritious recipes."""

import streamlit as st

from src.nutrition.models import (
    GeneratedRecipe,
    HealthProfile,
    NutritionData,
    PantryItem,
)
from src.nutrition.fda_guidelines import compute_dv_percentages


def _init_session_state():
    """Initialize session state keys for the recipe tab."""
    if "pantry_items" not in st.session_state:
        st.session_state.pantry_items = []
    if "generated_recipe" not in st.session_state:
        st.session_state.generated_recipe = None


def _render_pantry_builder():
    """Render the pantry builder section with label scan, food photo, and manual add."""
    col_scan, col_photo = st.columns(2)

    with col_scan:
        st.subheader("Scan a Label")
        uploaded_label = st.file_uploader(
            "Upload nutrition label",
            type=["jpg", "jpeg", "png", "heic", "heif", "webp"],
            key="recipe_label_upload",
        )
        if uploaded_label and st.button("Add from Label", key="add_label"):
            try:
                # Vision-first, Tesseract fallback — same strategy as the
                # Upload Label tab. Groq vision handles phone photos much
                # better than Tesseract + regex tuning.
                from src.vision.label_reader import extract_label_with_vision

                uploaded_label.seek(0)
                image_bytes = uploaded_label.read()
                uploaded_label.seek(0)

                nutrition = None
                vision_result = extract_label_with_vision(image_bytes)
                if vision_result is not None and vision_result.fields_parsed > 0:
                    nutrition = vision_result.nutrition
                    if vision_result.confidence < 0.5:
                        st.warning(
                            f"AI vision couldn't read this label clearly "
                            f"(only {vision_result.fields_parsed} field(s)). "
                            "The item was added but values may be incomplete."
                        )
                else:
                    # Fall back to Tesseract
                    from PIL import Image
                    from src.ocr.extractor import extract

                    uploaded_label.seek(0)
                    image = Image.open(uploaded_label).convert("RGB")
                    ocr_result = extract(image)
                    uploaded_label.seek(0)
                    nutrition = ocr_result.nutrition
                    if ocr_result.confidence == "low":
                        st.warning(
                            f"Couldn't read this label clearly — only "
                            f"{ocr_result.fields_parsed} field(s) detected. "
                            "The item was added but nutrition data may be sparse."
                        )

                item = PantryItem(
                    name="Scanned Item",
                    source="label_scan",
                    nutrition=nutrition,
                    quantity="1 serving",
                )
                st.session_state.pantry_items.append(item)
                st.success(f"Added: {item.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Label reading failed: {e}. Try manual entry instead.")

    with col_photo:
        st.subheader("Snap Food Items")
        food_photo = st.file_uploader(
            "Upload food photo",
            type=["jpg", "jpeg", "png", "heic", "heif", "webp"],
            key="recipe_food_upload",
        )
        if food_photo and st.button("Identify & Add", key="add_photo"):
            try:
                from src.vision.food_identifier import identify_food

                with st.spinner("Identifying food items..."):
                    foods = identify_food(food_photo.getvalue())
                for f in foods:
                    grams = f.get("estimated_grams")
                    item = PantryItem(
                        name=f["name"],
                        source="photo_id",
                        estimated_grams=grams,
                        quantity=f"{grams}g" if grams else "",
                    )
                    st.session_state.pantry_items.append(item)
                st.success(f"Added {len(foods)} item(s) from photo")
                st.rerun()
            except Exception as e:
                st.error(f"Food identification failed: {e}. Try manual entry instead.")

    # Manual add
    with st.expander("Or add manually"):
        manual_name = st.text_input("Ingredient name", key="manual_ingredient")
        manual_qty = st.text_input(
            "Quantity (e.g., '2 cups', '1 can')", key="manual_qty"
        )
        if st.button("Add Ingredient", key="add_manual") and manual_name:
            st.session_state.pantry_items.append(
                PantryItem(name=manual_name, source="manual", quantity=manual_qty)
            )
            st.rerun()


def _render_pantry_display():
    """Render the current pantry contents with remove buttons."""
    items = st.session_state.pantry_items
    st.subheader(f"Your Pantry ({len(items)} items)")

    if not items:
        st.info("Add ingredients above to get started.")
        return

    for i, item in enumerate(items):
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            st.write(f"**{item.name}**")
        with col2:
            st.write(item.quantity or "-")
        with col3:
            source_labels = {
                "label_scan": "Label",
                "photo_id": "Photo",
                "manual": "Manual",
            }
            st.caption(source_labels.get(item.source, item.source))
        with col4:
            if st.button("Remove", key=f"remove_{i}"):
                st.session_state.pantry_items.pop(i)
                st.rerun()

    if st.button("Clear All", key="clear_pantry"):
        st.session_state.pantry_items = []
        st.session_state.generated_recipe = None
        st.rerun()


def _render_recipe_generation():
    """Render the recipe generation button and results."""
    st.divider()
    items = st.session_state.pantry_items

    if len(items) < 2:
        if items:
            st.warning("Add at least 2 ingredients to generate a recipe.")
        return

    col_gen, col_regen = st.columns([1, 1])
    with col_gen:
        generate = st.button("Generate Recipe", type="primary", key="gen_recipe")
    with col_regen:
        if st.session_state.generated_recipe:
            regenerate = st.button("Regenerate", key="regen_recipe")
        else:
            regenerate = False

    if generate or regenerate:
        with st.spinner("Creating your recipe..."):
            try:
                from src.llm.groq_client import GroqClient

                health_profile = st.session_state.get(
                    "health_profile", HealthProfile()
                )
                client = GroqClient()
                recipe = client.generate_recipe(items, health_profile)
                st.session_state.generated_recipe = recipe
                st.rerun()
            except Exception as e:
                st.error(f"Recipe generation failed: {e}")
                return

    # Display generated recipe
    recipe: GeneratedRecipe | None = st.session_state.generated_recipe
    if not recipe:
        return

    st.subheader(f"{recipe.title}")
    st.write(f"*Serves {recipe.servings}*")

    col_ing, col_steps = st.columns(2)
    with col_ing:
        st.markdown("**Ingredients:**")
        for ing in recipe.ingredients_used:
            st.markdown(f"- {ing}")
        if recipe.additional_ingredients_needed:
            st.markdown("**You may also need:**")
            for ing in recipe.additional_ingredients_needed:
                st.markdown(f"- {ing}")

    with col_steps:
        st.markdown("**Instructions:**")
        for j, step in enumerate(recipe.instructions, 1):
            st.markdown(f"{j}. {step}")

    # Nutrition breakdown
    if recipe.estimated_nutrition:
        st.subheader("Estimated Nutrition (per serving)")
        dv = compute_dv_percentages(recipe.estimated_nutrition)

        # Display as a simple bar chart
        import pandas as pd

        dv_display = {k.replace("_", " ").title(): v for k, v in dv.items()}
        df = pd.DataFrame(
            {"Nutrient": list(dv_display.keys()), "% Daily Value": list(dv_display.values())}
        )
        df = df.set_index("Nutrient")
        st.bar_chart(df)

    # Highlights and tips
    if recipe.nutrition_highlights:
        st.markdown(
            "**Nutrition Highlights:** " + " | ".join(recipe.nutrition_highlights)
        )
    if recipe.tips:
        st.info(f"**Tip:** {recipe.tips}")

    st.caption("*Nutrition values are AI-estimated and may not be precise.*")


def render_recipe_tab():
    """Main entry point for the Recipe Generator tab."""
    st.header("Recipe Generator")
    st.caption(
        "Add ingredients from label scans or food photos, then generate a "
        "nutritious recipe. Designed to help you make the most of what you have."
    )

    _init_session_state()
    _render_pantry_builder()
    _render_pantry_display()
    _render_recipe_generation()
