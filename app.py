import streamlit as st

st.set_page_config(
    page_title="NutriScan",
    page_icon="🔍",
    layout="wide",
)

st.title("NutriScan")
st.subheader("AI-Powered Food Nutrition Label Analyzer")

# Sidebar — health profile placeholder
with st.sidebar:
    st.header("Your Health Profile")
    st.info("Health profile settings will appear here.")

# Main area — four tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📷 Upload Label", "🍔 Snap Food", "✏️ Manual Entry", "🍳 Recipe Generator"]
)

with tab1:
    st.write("Upload a photo of a nutrition label to get started.")

with tab2:
    st.write("Snap a photo of your food to identify it and get nutrition info.")

with tab3:
    st.write("Manually enter nutrition information.")

with tab4:
    from src.ui.pages_recipe import render_recipe_tab

    render_recipe_tab()
