import streamlit as st

st.set_page_config(
    page_title="NutriScan",
    page_icon="🥗",
    layout="wide",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════
   NutriScan Global Theme
   ═══════════════════════════════════════════════════════════ */

/* Page background */
[data-testid="stAppViewContainer"] > .main {
    background-color: #F4FAF4;
}
.block-container {
    padding-top: 0.75rem !important;
    padding-bottom: 2rem;
    max-width: 1080px;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(165deg, #1A4D1E 0%, #2E7D32 55%, #388E3C 100%);
    padding-top: 0.5rem;
}
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stSelectbox > div > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div > div {
    background: rgba(255,255,255,0.14) !important;
    border-color: rgba(255,255,255,0.32) !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: rgba(255,255,255,0.22) !important;
    border-color: rgba(255,255,255,0.4) !important;
}
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.14) !important;
    border-color: rgba(255,255,255,0.32) !important;
    color: white !important;
}
[data-testid="stSidebar"] input::placeholder { color: rgba(255,255,255,0.5) !important; }
[data-testid="stSidebar"] [data-testid="stInfo"] {
    background: rgba(255,255,255,0.12) !important;
    border: none !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2) !important;
    margin: 0.75rem 0 !important;
}
[data-testid="stSidebar"] label {
    color: rgba(255,255,255,0.82) !important;
    font-size: 0.83rem !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: rgba(255,255,255,0.88) !important; }
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: rgba(255,255,255,0.6) !important;
}
/* Sidebar number input arrows */
[data-testid="stSidebar"] button[aria-label="decrement"],
[data-testid="stSidebar"] button[aria-label="increment"] {
    background: rgba(255,255,255,0.15) !important;
    border-color: rgba(255,255,255,0.3) !important;
}

/* ── Tabs ───────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: white;
    border-radius: 14px;
    padding: 5px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    gap: 3px;
    margin-bottom: 0.5rem;
}
[data-testid="stTabs"] button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.2s ease, color 0.2s ease !important;
    padding: 0.35rem 0.55rem !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #2E7D32, #43A047) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(46,125,50,0.35) !important;
}
[data-testid="stTabs"] button p { font-size: 0.82rem; }
[data-testid="stTabsContent"] { padding-top: 0.5rem; }

/* Sub-tabs (e.g. pantry builder inside recipe tab) */
[data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"] {
    box-shadow: none;
    border: 1px solid #E8F5E9;
    background: #F9FDF9;
    padding: 4px;
}
[data-testid="stTabs"] [data-testid="stTabs"] button[aria-selected="true"] {
    background: #E8F5E9 !important;
    color: #1B5E20 !important;
    box-shadow: none !important;
}

/* ── Primary Buttons ────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2E7D32 0%, #43A047 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 2px 8px rgba(46,125,50,0.28) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    padding: 0.45rem 1.2rem !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(46,125,50,0.40) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    border-color: #81C784 !important;
    color: #2E7D32 !important;
    font-weight: 600 !important;
    transition: background 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #E8F5E9 !important;
    border-color: #2E7D32 !important;
}

/* ── Download button ─────────────────────────────────────── */
.stDownloadButton > button {
    border-radius: 10px !important;
    border-color: #81C784 !important;
    color: #2E7D32 !important;
    font-weight: 600 !important;
    transition: background 0.15s ease !important;
}
.stDownloadButton > button:hover {
    background: #E8F5E9 !important;
    border-color: #2E7D32 !important;
}

/* ── File Uploader ────────────────────────────────────────── */
[data-testid="stFileUploadDropzone"] {
    border-radius: 14px !important;
    border: 2px dashed #81C784 !important;
    background: #F9FDF9 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    background: #E8F5E9 !important;
    border-color: #2E7D32 !important;
}

/* ── Expanders ────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border-radius: 12px !important;
    border: 1px solid #C8E6C9 !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
    background: white !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    background: #F9FDF9 !important;
    padding: 0.65rem 1rem !important;
    transition: background 0.15s ease !important;
}
[data-testid="stExpander"] summary:hover { background: #E8F5E9 !important; }
[data-testid="stExpander"] summary svg { color: #2E7D32 !important; }

/* ── Alerts ─────────────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Metrics ────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #E8F5E9;
}
[data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; }

/* ── Dividers ─────────────────────────────────────────────── */
hr { border-color: #E8F5E9 !important; margin: 1.25rem 0 !important; }

/* ── Forms ────────────────────────────────────────────────── */
[data-testid="stForm"] {
    border: 1px solid #E8F5E9 !important;
    border-radius: 14px !important;
    background: white !important;
    padding: 0.5rem 0.75rem !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04) !important;
}

/* ── Inputs ───────────────────────────────────────────────── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #66BB6A !important;
    box-shadow: 0 0 0 2px rgba(102,187,106,0.2) !important;
}

/* ── Camera input ─────────────────────────────────────────── */
[data-testid="stCameraInput"] { border-radius: 14px !important; overflow: hidden; }

/* ── Caption ──────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] { color: #6A8A6A !important; }

/* ── Bar chart ────────────────────────────────────────────── */
[data-testid="stVegaLiteChart"] { border-radius: 12px !important; overflow: hidden; }

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F4FAF4; }
::-webkit-scrollbar-thumb { background: #A5D6A7; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #66BB6A; }

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #2E7D32 !important; }

/* ── Progress bar (st.progress) ──────────────────────────── */
[data-testid="stProgress"] > div { background-color: #E8F5E9 !important; }
[data-testid="stProgress"] > div > div { background-color: #43A047 !important; }

/* ── Image caption ────────────────────────────────────────── */
[data-testid="stImage"] figcaption {
    text-align: center;
    font-size: 0.78rem;
    color: #6A8A6A;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1A4D1E 0%, #2E7D32 40%, #43A047 100%);
    color: white;
    padding: 1.6rem 2.2rem 1.4rem;
    border-radius: 18px;
    margin-bottom: 0.75rem;
    box-shadow: 0 4px 24px rgba(46,125,50,0.30);
">
    <div style="display:flex; align-items:center; gap:1rem; margin-bottom:0.5rem;">
        <div style="font-size:2.4rem; line-height:1;
                    filter:drop-shadow(0 2px 6px rgba(0,0,0,0.25));">🥗</div>
        <div>
            <div style="font-size:2rem; font-weight:900; letter-spacing:-0.5px;
                        line-height:1.1;">NutriScan</div>
            <div style="opacity:0.80; font-size:0.88rem; margin-top:2px;
                        letter-spacing:0.1px;">
                AI-powered nutrition intelligence &amp; free food access
            </div>
        </div>
    </div>
    <div style="display:flex; gap:7px; flex-wrap:wrap; margin-top:0.9rem;">
        <span style="background:rgba(255,255,255,0.18);padding:4px 13px;
                     border-radius:100px;font-size:0.77rem;font-weight:600;">
            📷 Label Scanning</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 13px;
                     border-radius:100px;font-size:0.77rem;font-weight:600;">
            🍽️ Food Recognition</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 13px;
                     border-radius:100px;font-size:0.77rem;font-weight:600;">
            ✏️ Manual Entry</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 13px;
                     border-radius:100px;font-size:0.77rem;font-weight:600;">
            🍳 Recipe Generator</span>
        <span style="background:rgba(255,255,255,0.18);padding:4px 13px;
                     border-radius:100px;font-size:0.77rem;font-weight:600;">
            📍 Free Food Finder</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── How-to guide (collapsible) ────────────────────────────────────────────────
with st.expander("📖 How to use NutriScan", expanded=False):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        <div style="padding:0.25rem 0.5rem;">
            <div style="font-weight:800;color:#1B5E20;margin-bottom:0.5rem;font-size:0.95rem;">
                🔬 Analyze Nutrition
            </div>
            <div style="font-size:0.83rem;color:#444;line-height:1.6;">
                <strong>📷 Upload Label</strong> — photograph any nutrition label; AI reads it for you.<br><br>
                <strong>🍔 Snap Food</strong> — photograph your meal; AI identifies each food and estimates portions.<br><br>
                <strong>✏️ Manual Entry</strong> — type values in by hand when you have the numbers.
            </div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div style="padding:0.25rem 0.5rem;border-left:2px solid #C8E6C9;">
            <div style="font-weight:800;color:#1B5E20;margin-bottom:0.5rem;font-size:0.95rem;">
                🍳 Generate Recipes
            </div>
            <div style="font-size:0.83rem;color:#444;line-height:1.6;">
                <strong>Add ingredients</strong> by scanning labels, photographing food,
                or typing them in.<br><br>
                <strong>Generate Recipe</strong> — the AI creates a nutritious recipe from
                exactly what you have, respecting your dietary goals and allergen settings.<br><br>
                <strong>Download</strong> the recipe as a text file to save or share.
            </div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""
        <div style="padding:0.25rem 0.5rem;border-left:2px solid #C8E6C9;">
            <div style="font-weight:800;color:#1B5E20;margin-bottom:0.5rem;font-size:0.95rem;">
                📍 Find Free Food
            </div>
            <div style="font-size:0.83rem;color:#444;line-height:1.6;">
                <strong>Enter a zip code</strong> to find nearby food banks, pantries,
                free meal programs, community gardens, and SNAP/WIC retailers.<br><br>
                <strong>Nutrient gaps</strong> from your recent scan are shown, plus
                <strong>AI-generated advice</strong> on which local resources can help
                fill each gap for free.
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#E8F5E9;border-radius:10px;padding:0.65rem 1rem;
                margin-top:0.5rem;font-size:0.82rem;color:#1B5E20;">
        💡 <strong>Tip:</strong> Set your <strong>Health Profile</strong> in the sidebar
        (allergens, dietary goals, caloric target) before analyzing — it makes every
        recommendation and allergen flag personal to you.
    </div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center; padding:0.75rem 0 0.25rem;">
    <div style="font-size:2.2rem; margin-bottom:0.3rem;
                filter:drop-shadow(0 2px 4px rgba(0,0,0,0.2));">👤</div>
    <div style="font-size:1.05rem; font-weight:800; letter-spacing:0.2px;">
        Health Profile</div>
    <div style="opacity:0.68; font-size:0.76rem; margin-top:2px;">
        Personalize your analysis</div>
</div>
""", unsafe_allow_html=True)

from src.ui.components import health_profile_form
health_profile_form()

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📷 Upload Label", "🍔 Snap Food", "✏️ Manual Entry",
     "🍳 Recipe Generator", "📍 Find Free Food"]
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
