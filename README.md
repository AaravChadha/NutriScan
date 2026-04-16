# NutriScan

**AI-Powered Nutrition Assistant for Combating Food Insecurity**

Built by three Purdue University freshmen for the **Purdue Undergraduate Research Symposium** (April 16, 2026) through [Dataception](https://dataception.org).

---

NutriScan reads nutrition labels, identifies food from photos, generates nutritious recipes from available ingredients, and connects users to free food resources nearby. Every API in the stack is free — designed to be accessible to anyone.

## Demo

[![NutriScan walkthrough video](https://img.youtube.com/vi/ZuMDxK2uLQk/maxresdefault.jpg)](https://youtu.be/ZuMDxK2uLQk)

A walkthrough covering label scanning, allergen detection, goal conflicts, preservative flagging, food photo analysis, recipe generation, and free-resource recommendations.

## Features

| Feature | What it does |
|---------|-------------|
| **Upload Label** | Photo of any nutrition label &rarr; AI vision extracts values &rarr; allergen/preservative/nutrient analysis against your health profile |
| **Snap Food** | Photo of your meal &rarr; AI identifies items + estimates portions &rarr; USDA nutrition lookup &rarr; full analysis |
| **Manual Entry** | Type nutrition values by hand when scanning isn't practical |
| **Recipe Generator** | Build a pantry from scans, photos, or manual input &rarr; AI generates a nutritious recipe from what you have. Maximize nutrition from limited ingredients |
| **Find Free Food** | Enter a zip code &rarr; nearby food banks, pantries, free meals, SNAP/WIC, community gardens. Shows your nutrient gaps + AI advice connecting deficiencies to specific free resources |

A **Health Profile** sidebar (allergens, dietary goals, caloric target, restrictions) personalizes every analysis and recipe.

## Team

### Aarav Chadha
- **Project planning & architecture** — authored the full build plan (phases, task division, tech-stack decisions).
- **Foundations (Phases 1–2)** — scaffolding, data models (`NutritionData`, `HealthProfile`, `AnalysisResult`), FDA daily-value JSON, and DV% computation.
- **LLM integration (Phase 3.2)** — analysis prompts, Groq client (`analyze()`), JSON response parsing, retry-on-rate-limit, unit tests.
- **Open Food Facts fallback (Phase 3.3.1.5)** — `lookup_food()` wrapper that tries USDA first, falls back to OFF for branded products.
- **Food photo recognition (Phase 3.4)** — vision prompts, Groq vision client (Llama 4 Scout), USDA/OFF bridge (`lookup_food_nutrition`, `aggregate_nutrition`).
- **Recipe generator (Phase 3.5)** — models, prompts, Groq recipe client, and pantry-aware UI.
- **Vision-based label reader** — replaced Tesseract on the golden path (`src/vision/label_reader.py`), with HEIC/HEIF support via `pillow-heif` and Tesseract kept as offline fallback.
- **OCR real-image validation (Phase 3.1.3)** — collected real label photos, surfaced 3 regex bugs, added 16 integration tests.
- **Integration (Phase 4)** — pipeline wire-up, UX flow verification across all 5 tabs, error handling (OCR confidence banners, graceful API degradation).
- **LLM evaluation (Phase 5.1)** — 5 test cases, scoring harness, **29/30 checks passed (96.7%)**.
- **UI polish (Phase 7.1)** — theme-adaptive dark mode across all pages, scroll-hijack fix on number inputs, toast notifications, condensed hero header.
- **Final error-handling pass (Phase 7.1.3)** — vision MIME detection + HEIC re-encoding, DV% rendering fix, Snap Food float-confidence bucketing, katsu-vs-sushi disambiguation, multi-upload pantry.
- **README, video walkthrough, and presentation deck (Phases 7.1.4, 7.2–7.5)** — recorded and edited the walkthrough, authored slides (problem, architecture, eval, future work), wrote day-of script.

### Neil Sachdev
- **OCR preprocessor (Phase 3.1.1)** — PIL/path/numpy loader, grayscale, upscale, adaptive threshold, Gaussian blur.
- **OCR extractor (Phase 3.1.2)** — Tesseract invocation with `--psm 6`, per-nutrient regex patterns, ingredients parser, confidence indicator.
- **OCR unit tests (Phase 3.1.3.3/3.1.3.4)** — hardcoded-string tests covering clean, spaced, decimal, sparse, and noisy label formats.
- **Nutrient gap analysis (Phase 6.1)** — `analyze_nutrient_gaps()` compares intake against FDA daily values at a 25% threshold, maps 13 nutrients to concrete food suggestions.
- **Local resource lookup (Phase 6.2)** — `find_local_resources()` with 11 curated West Lafayette / Lafayette entries across all 7 resource types (food banks, pantries, free meal programs, SNAP/WIC, community gardens, subsidized farmers markets). No regular grocery stores — only free or income-qualified resources.
- **LLM recommendation layer (Phase 6.3)** — `recommend_resources()` generating personalized advice connecting specific deficiencies to specific nearby resources.

### Nuv Ahuja
- **USDA API client & preservative checker (Phase 3.3.1)** — `search_food()`, `check_preservatives()` with hardcoded preservative list, session-state caching.
- **Health profile sidebar (Phase 3.3.2)** — caloric target, allergens, dietary goals, restrictions.
- **Nutrition editor widget (Phase 3.3.3)** — shared editable form used across Upload, Manual, Snap, and Recipe tabs.
- **Results display (Phase 3.3.4)** — colored allergen/preservative flags, DV% bar chart, recommendations, risk summary.
- **Page scaffolds (Phases 3.3.5, 3.3.6, 3.4.4)** — Upload Label, Manual Entry, and Snap Food pages with camera input, editable food table, and pipeline wiring.
- **App tab wiring** — all 5 tabs in `app.py`.
- **Find Free Food tab UI (Phase 6.4)** — zip code input, colorized nutrient gap cards, resource cards per type, personalized advice button.
- **UI overhaul (Phase 7.1)** — global CSS theme, A+→F nutritional grade badge, 4-tile quick-stats row, custom progress bar chart, color-coded resource cards, source badges on pantry items, recipe card with two-column layout.
- **Slide visual polish (Phase 7.4)** — layout, typography, and styling pass over the deck.

## Tech Stack

All-free, no paid dependencies.

| Component | Technology |
|-----------|-----------|
| **Frontend** | Python + Streamlit |
| **Label & Food Vision** | Groq Vision API &mdash; Llama 4 Scout (`meta-llama/llama-4-scout-17b-16e-instruct`) |
| **LLM Analysis & Recipes** | Groq Text API &mdash; Llama 3.3-70b-versatile |
| **Nutrition Data** | USDA FoodData Central API + Open Food Facts API (fallback) |
| **OCR Fallback** | Tesseract via pytesseract + OpenCV |
| **iPhone Photo Support** | pillow-heif (HEIC/HEIF native) |
| **Food Resources** | Curated West Lafayette / Lafayette database |

## Getting Started

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) *(only needed for offline OCR fallback)*
  - macOS: `brew install tesseract`
  - Ubuntu: `apt install tesseract-ocr`

### Installation

```bash
git clone https://github.com/AaravChadha/NutriScan.git
cd NutriScan

python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your free keys:

```env
# https://console.groq.com/keys
GROQ_API_KEY=your_key_here

# https://api.data.gov/signup/
USDA_API_KEY=your_key_here
```

### Run

```bash
streamlit run app.py
```

Opens at [http://localhost:8501](http://localhost:8501). Set your Health Profile in the sidebar before analyzing.

## Project Structure

```
NutriScan/
├── app.py                          # Streamlit entry point + global theme
├── .streamlit/config.toml          # Dark theme + green accent config
├── src/
│   ├── ocr/                        # Tesseract OCR fallback
│   │   ├── preprocessor.py         #   OpenCV preprocessing (EXIF, threshold, blur)
│   │   └── extractor.py            #   OCR invocation + regex parsing
│   ├── llm/
│   │   ├── groq_client.py          #   Groq API wrapper (analyze, recipe, resources)
│   │   └── prompts.py              #   All prompt templates
│   ├── nutrition/
│   │   ├── models.py               #   Dataclasses (NutritionData, HealthProfile, etc.)
│   │   ├── fda_guidelines.py       #   FDA daily value % computation
│   │   ├── usda_client.py          #   USDA API + fallback wrapper
│   │   └── openfoodfacts_client.py #   Open Food Facts API client
│   ├── vision/
│   │   ├── food_identifier.py      #   Groq vision -> food items + USDA bridge
│   │   └── label_reader.py         #   Groq vision -> NutritionData
│   ├── resources/
│   │   └── locator.py              #   Nutrient gap analysis + local resource finder
│   └── ui/
│       ├── components.py           #   Health profile form, nutrition editor
│       ├── pages_upload.py         #   Upload Label tab
│       ├── pages_snap.py           #   Snap Food tab
│       ├── pages_manual.py         #   Manual Entry tab
│       ├── pages_recipe.py         #   Recipe Generator tab
│       ├── pages_find.py           #   Find Free Food tab
│       └── pages_results.py        #   Analysis results display
├── data/
│   └── fda_daily_values.json       # FDA 2,000-calorie reference values
├── tests/
│   ├── test_ocr.py                 # OCR preprocessor + extractor tests
│   ├── test_llm.py                 # Prompt + response parsing tests
│   ├── test_nutrition.py           # Data model + DV% tests
│   └── sample_labels/              # Real nutrition label photos for integration tests
└── eval/
    ├── llm_test_cases.py           # 5 hand-crafted test cases
    ├── llm_accuracy.py             # Evaluation runner + scorer
    ├── llm_accuracy_report.md      # Human-readable results (29/30, 96.7%)
    └── llm_accuracy_results.json   # Machine-readable results
```

## Running Tests & Evaluation

**Unit + integration tests:**

```bash
pytest tests/
```

80 tests covering OCR parsing, data models, FDA DV% math, prompt construction, response parsing, and real-image extraction.

**LLM evaluation:**

```bash
python -m eval.llm_accuracy
```

Runs 5 test cases through the live Groq API and regenerates [`eval/llm_accuracy_report.md`](eval/llm_accuracy_report.md). Requires `GROQ_API_KEY` in `.env`.

## Evaluation Results

| Dimension | Pass Rate |
|-----------|-----------|
| Allergen detection | 100% |
| Preservative flagging | 100% |
| Nutrient concern identification | 100% |
| Goal alignment | 100% |
| Risk rating | 80% |
| **Overall** | **96.7% (29/30)** |

5 test cases covering clean-pass, allergen detection, preservative flagging, goal conflict, and multi-issue cascade. Full results in [`eval/llm_accuracy_report.md`](eval/llm_accuracy_report.md).

## License

This project was built for academic research purposes at Purdue University.
