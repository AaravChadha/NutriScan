"""USDA FoodData Central API client."""

import os

import requests
import streamlit as st

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


def search_food(query: str, api_key: str) -> dict:
    """Search USDA FoodData Central for a food item.

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

    params = {
        "query": query,
        "api_key": api_key,
        "pageSize": 5,
        "dataType": ["SR Legacy", "Survey (FNDDS)"],
    }
    response = requests.get(
        f"{USDA_BASE_URL}/foods/search", params=params, timeout=10
    )
    response.raise_for_status()
    result = response.json()
    st.session_state[cache_key] = result
    return result


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
