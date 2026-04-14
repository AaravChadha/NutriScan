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
   NutriScan Theme — works with Streamlit light AND dark mode
   No forced backgrounds. Green accent only. Let Streamlit
   handle bg/text colors so both modes look correct.
   ═══════════════════════════════════════════════════════════ */

/* Override Streamlit's root accent color (kills red hover globally) */
:root {
    --primary-color: #4CAF50 !important;
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem;
    max-width: 1080px;
}

/* ── Sidebar — matches app theme, green accent ───────────── */
[data-testid="stSidebar"] > div:first-child {
    border-right: 2px solid #2E7D32;
    padding-top: 0.5rem;
}
[data-testid="stSidebar"] label {
    font-size: 0.83rem !important;
}
[data-testid="stSidebar"] hr {
    margin: 0.75rem 0 !important;
}

/* ── Tabs — green accent, transparent bg ─────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-radius: 14px;
    padding: 5px;
    gap: 3px;
    margin-bottom: 0.5rem;
    border-bottom: none !important;
}
[data-testid="stTabs"] button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.2s ease, color 0.2s ease !important;
    padding: 0.35rem 0.55rem !important;
    background: transparent !important;
    border-bottom: none !important;
}
[data-testid="stTabs"] button:hover {
    background: rgba(76,175,80,0.12) !important;
    color: #66BB6A !important;
}
[data-testid="stTabs"] button:hover p {
    color: #66BB6A !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #2E7D32, #43A047) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(46,125,50,0.35) !important;
    border-bottom: none !important;
}
[data-testid="stTabs"] button[aria-selected="true"]:hover {
    background: linear-gradient(135deg, #2E7D32, #43A047) !important;
    color: white !important;
}
[data-testid="stTabs"] button[aria-selected="true"]:hover p {
    color: white !important;
}
[data-testid="stTabs"] button p { font-size: 0.82rem; }
/* Kill ALL Streamlit tab indicators (red/blue underlines, ::before, ::after) */
[data-testid="stTabs"] button::before,
[data-testid="stTabs"] button::after,
[data-testid="stTabs"] button[aria-selected="true"]::before,
[data-testid="stTabs"] button[aria-selected="true"]::after {
    display: none !important;
    height: 0 !important;
    border: none !important;
    background: none !important;
}
[data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTabs"] [role="tablist"]::before {
    display: none !important;
}
/* Override any bottom-border indicator */
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
    background: none !important;
}
[data-testid="stTabsContent"] { padding-top: 0.5rem; }

/* Sub-tabs */
[data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"] {
    box-shadow: none;
    padding: 4px;
}
[data-testid="stTabs"] [data-testid="stTabs"] button[aria-selected="true"] {
    box-shadow: none !important;
}

/* ── Primary Buttons — always green ──────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2E7D32 0%, #43A047 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 2px 8px rgba(46,125,50,0.28) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    padding: 0.45rem 1.2rem !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(46,125,50,0.40) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.15s ease !important;
}
.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: background 0.15s ease !important;
}

/* ── Shape-only overrides (no forced colors) ─────────────── */
[data-testid="stFileUploadDropzone"] {
    border-radius: 14px !important;
    border: 2px dashed #43A047 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stExpander"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    transition: background 0.15s ease !important;
}
[data-testid="stExpander"] summary svg { color: #2E7D32 !important; }
[data-testid="stAlert"] { border-radius: 10px !important; }
[data-testid="stMetric"] {
    border-radius: 12px;
    padding: 0.75rem 1rem;
}
[data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; }
hr { margin: 1.25rem 0 !important; }
[data-testid="stForm"] {
    border-radius: 14px !important;
    padding: 0.5rem 0.75rem !important;
}
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
[data-testid="stCameraInput"] { border-radius: 14px !important; overflow: hidden; }
[data-testid="stVegaLiteChart"] { border-radius: 12px !important; overflow: hidden; }

/* ── Override Streamlit's red/blue hover & accent colors ──── */
a, a:visited { color: #4CAF50 !important; }
a:hover { color: #66BB6A !important; }
/* Buttons, expanders, interactive elements */
[data-testid="stExpander"] summary:hover span,
[data-testid="stExpander"] summary:hover p {
    color: #66BB6A !important;
}
/* Checkbox label hover */
.stCheckbox label:hover span { color: #66BB6A !important; }
/* Number input +/- buttons */
button[aria-label="decrement"]:hover,
button[aria-label="increment"]:hover {
    color: #4CAF50 !important;
    border-color: #4CAF50 !important;
}
/* File uploader text */
[data-testid="stFileUploadDropzone"] span:hover { color: #66BB6A !important; }
/* Generic interactive text hover — override red globally */
*:hover > [data-testid="stMarkdownContainer"] { color: inherit; }

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #A5D6A7; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #66BB6A; }

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #2E7D32 !important; }

/* ── Progress bar ─────────────────────────────────────────── */
[data-testid="stProgress"] > div > div { background-color: #43A047 !important; }

/* ── Image caption ────────────────────────────────────────── */
[data-testid="stImage"] figcaption {
    text-align: center;
    font-size: 0.78rem;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Fix: prevent number inputs from hijacking scroll ─────────────────────────
st.markdown("""
<script>
document.addEventListener('wheel', function(e) {
    if (document.activeElement && document.activeElement.type === 'number') {
        document.activeElement.blur();
    }
}, {passive: true});
// Also prevent wheel on any number input even when not focused
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type=number]').forEach(function(el) {
        el.addEventListener('wheel', function(e) { this.blur(); }, {passive: true});
    });
});
// Re-apply after Streamlit rerenders (MutationObserver)
new MutationObserver(function() {
    document.querySelectorAll('input[type=number]').forEach(function(el) {
        if (!el.dataset.noScroll) {
            el.dataset.noScroll = '1';
            el.addEventListener('wheel', function(e) { this.blur(); }, {passive: true});
        }
    });
}).observe(document.body, {childList: true, subtree: true});
</script>
""", unsafe_allow_html=True)

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #0D2B0D 0%, #163016 50%, #1A3A1A 100%);
    color: rgba(255,255,255,0.92);
    padding: 0.75rem 1.5rem;
    border-radius: 10px;
    margin-bottom: 0.6rem;
    border: 1px solid rgba(46,125,50,0.3);
    overflow: visible;
">
    <div style="display:flex; align-items:center; gap:0.7rem;">
        <div style="font-size:1.6rem; line-height:1;">🥗</div>
        <span style="font-size:1.4rem; font-weight:900; letter-spacing:-0.3px; color:#4CAF50;">NutriScan</span>
        <span style="opacity:0.65; font-size:0.78rem; letter-spacing:0.1px;">
            AI-powered nutrition intelligence &amp; free food access
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Quick tips (collapsible, lightweight) ─────────────────────────────────────
with st.expander("💡 Quick tips", expanded=False):
    st.markdown("""
    <div style="font-size:0.83rem;line-height:1.7;opacity:0.75;">
        <strong>📷 Upload Label</strong> — photo of a nutrition label, AI extracts the data<br>
        <strong>🍔 Snap Food</strong> — photo of your meal, AI identifies items + portions<br>
        <strong>✏️ Manual</strong> — type values by hand<br>
        <strong>🍳 Recipes</strong> — build a pantry, generate a nutritious recipe<br>
        <strong>📍 Free Food</strong> — find food banks and free resources near you<br><br>
        Set your <strong>Health Profile</strong> in the sidebar first for personalized results.
    </div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:0.6rem; padding:0.5rem 0 0.25rem;">
    <div style="width:32px;height:32px;background:#2E7D32;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-size:1rem;flex-shrink:0;">🥗</div>
    <div>
        <div style="font-size:0.95rem; font-weight:800;">Health Profile</div>
        <div style="opacity:0.5; font-size:0.72rem;">Personalize your analysis</div>
    </div>
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
