"""USDA FoodData Central API client."""

import os

import requests
import streamlit as st

from src.nutrition.openfoodfacts_client import search_food_by_name as _off_search

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Common food preservatives to detect in ingredients lists
_PRESERVATIVES = [
    "sodium benzoate",
    "potassium sorbate",
    "calcium propionate",
    "sodium nitrate",
    "sodium nitrite",
    "bha",
    "bht",
    "butylated hydroxyanisole",
    "butylated hydroxytoluene",
    "tbhq",
    "tertiary butylhydroquinone",
    "sodium sulfite",
    "sulfur dioxide",
    "sodium metabisulfite",
    "disodium edta",
    "calcium disodium edta",
    "sodium erythorbate",
    "sodium acid pyrophosphate",
    "carrageenan",
    "monosodium glutamate",
    "artificial flavor",
    "artificial color",
    "red 40",
    "yellow 5",
    "yellow 6",
    "blue 1",
]


def _scrub_key(text: str, api_key: str) -> str:
    """Replace any occurrence of the API key in a string with a placeholder.

    USDA accepts the key in URL query strings, which means requests' built-in
    HTTPError messages will leak it on a 4xx/5xx. We use this to keep keys
    out of any error surface (st.error, logs, exception messages).
    """
    if not text or not api_key:
        return text
    return text.replace(api_key, "***REDACTED***")


def search_food(query: str, api_key: str) -> dict:
    """Search USDA FoodData Central for a food item.

    Uses the POST endpoint with a JSON body to avoid URL-encoding ambiguity
    around dataType values containing spaces and parentheses (e.g.
    "Survey (FNDDS)"), which caused intermittent 400 errors via GET. The
    api_key is sent via the X-Api-Key header so it never appears in URLs.

    Results are cached in st.session_state to avoid redundant API calls.

    Args:
        query: Food name to search for (e.g. "apple", "cheddar cheese").
        api_key: USDA FoodData Central API key.

    Returns:
        Parsed JSON response dict with 'foods' list and 'totalHits'.
    """
    cache_key = f"usda_search_{query.lower().strip()}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    body = {
        "query": query,
        "pageSize": 5,
        # Foundation + SR Legacy = curated raw foods; Survey (FNDDS) = mixed
        # dishes; Branded = packaged products as a last resort.
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"],
    }
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }

    try:
        response = requests.post(
            f"{USDA_BASE_URL}/foods/search",
            json=body,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
    except requests.HTTPError as e:
        # Re-raise with key scrubbed in case it sneaks into the URL/message
        raise requests.HTTPError(_scrub_key(str(e), api_key)) from None
    except requests.RequestException as e:
        raise type(e)(_scrub_key(str(e), api_key)) from None

    st.session_state[cache_key] = result
    return result


def lookup_food(query: str, api_key: str) -> dict:
    """Look up a food item across USDA + Open Food Facts.

    Tries USDA FoodData Central first (best for raw/whole foods). If USDA
    returns no results, falls back to Open Food Facts (best for branded
    packaged products like Pop-Tarts, Oreos, breakfast cereals).

    Args:
        query: Food name to search for.
        api_key: USDA FoodData Central API key.

    Returns:
        {
            "source": "usda" | "off" | None,
            "data": <raw response dict from the source>,
        }
        `source` is None if both lookups returned nothing.
    """
    try:
        usda_result = search_food(query, api_key)
        if usda_result.get("foods"):
            return {"source": "usda", "data": usda_result}
    except (requests.RequestException, ValueError):
        # USDA down, rate-limited, or returned non-JSON — fall through to OFF
        pass

    off_result = _off_search(query)
    if off_result.get("products"):
        return {"source": "off", "data": off_result}

    return {"source": None, "data": {}}


def check_preservatives(ingredients_list: str) -> list[str]:
    """Check an ingredients string for known preservatives.

    Args:
        ingredients_list: Raw ingredients text from a nutrition label.

    Returns:
        List of detected preservative names (title-cased), or empty list.
    """
    if not ingredients_list:
        return []
    lower = ingredients_list.lower()
    return [p.title() for p in _PRESERVATIVES if p in lower]
