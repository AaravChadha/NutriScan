"""Open Food Facts API client — fallback for branded/packaged foods.

USDA FoodData Central is curated for raw/whole foods (apple, chicken breast).
Open Food Facts is crowdsourced and covers branded packaged products much
better. Used as a fallback when USDA misses.

No API key required. A User-Agent header IS required — requests without one
get blocked with a non-JSON response.

CAVEAT: OFF's search endpoints (`cgi/search.pl` and `/api/v2/search`) are
known to load-shed with 503 "Page temporarily unavailable" responses during
high traffic. This client treats OFF as a best-effort fallback: on any
failure it returns an empty result so the caller can gracefully fall through
to manual entry. The barcode endpoint (`/api/v2/product/{barcode}`) is more
stable but not used here since NutriScan's pipeline gives us food names,
not barcodes.
"""

import requests
import streamlit as st

OFF_BASE_URL = "https://world.openfoodfacts.org"

# Open Food Facts requires a User-Agent header identifying the app.
# Without this, the API returns a block page / non-JSON response.
# See: https://openfoodfacts.github.io/openfoodfacts-server/api/
_OFF_USER_AGENT = "NutriScan/1.0 (https://github.com/AaravChadha/NutriScan)"


def search_food_by_name(query: str) -> dict:
    """Search Open Food Facts for a food item by name.

    Results are cached in st.session_state to avoid redundant calls.

    Args:
        query: Food name to search for (e.g. "pop tart", "oreo").

    Returns:
        Parsed JSON response dict with 'products' list and 'count'.
        Returns {'products': [], 'count': 0} on network failure.
    """
    cache_key = f"off_search_{query.lower().strip()}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
    }
    try:
        response = requests.get(
            f"{OFF_BASE_URL}/cgi/search.pl",
            params=params,
            headers={"User-Agent": _OFF_USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        result = {"products": [], "count": 0}

    st.session_state[cache_key] = result
    return result
