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

# Main area — two tabs
tab1, tab2 = st.tabs(["📷 Upload Label", "✏️ Manual Entry"])

with tab1:
    st.write("Upload a photo of a nutrition label to get started.")

with tab2:
    st.write("Manually enter nutrition information.")
