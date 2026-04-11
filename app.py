import streamlit as st

st.set_page_config(
    page_title="NutriScan",
    page_icon="🔍",
    layout="wide",
)

st.title("NutriScan")
st.subheader("AI-Powered Nutrition Assistant")

# Sidebar — health profile
from src.ui.components import health_profile_form
health_profile_form()

# Main area — five tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📷 Upload Label", "🍔 Snap Food", "✏️ Manual Entry", "🍳 Recipe Generator", "📍 Find Free Food"]
)

with tab1:
    from src.ui.pages_upload import render_upload_tab
    render_upload_tab()

with tab2:
    from src.ui.pages_snap import render_snap_tab
    render_snap_tab()

with tab3:
    from src.ui.pages_manual import render_manual_tab
    render_manual_tab()

with tab4:
    from src.ui.pages_recipe import render_recipe_tab
    render_recipe_tab()

with tab5:
    from src.ui.pages_find import render_find_tab
    render_find_tab()
