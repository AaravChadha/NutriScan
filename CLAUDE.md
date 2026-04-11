# NutriScan Build Plan

## Context
NutriScan is an AI-powered nutrition assistant that combats food insecurity through personalized dietary insights. It scans nutrition labels (OCR), identifies food from photos (vision AI), generates nutritious recipes from available ingredients, and connects users to free/low-income food resources nearby. Built by 3 Purdue freshmen (Aarav, Neil, Nuv) through Dataception for the undergraduate research symposium on **April 16, 2026**. All-free tech stack.

## Tech Stack
- **Python** + **Streamlit** (pure Python frontend)
- **Tesseract** via `pytesseract` + **OpenCV** for OCR
- **Groq API** with Llama 3.3-70b-versatile + Llama 3.2-90b-vision-preview (free tier)
- **USDA FoodData Central API** (free key from api.data.gov)
- **Food resource locator API** (TBD — USDA Food Desert Atlas, FoodFinder, Feeding America, or 211.org; fallback: curated local list)
- API keys in `.env` (gitignored), `.env.example` committed for teammates

## Project Structure
```
NutriScan/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── .env.example                # GROQ_API_KEY=  USDA_API_KEY=
├── .env                        # actual keys (gitignored)
├── .gitignore
├── src/
│   ├── ocr/
│   │   ├── preprocessor.py     # OpenCV image preprocessing
│   │   └── extractor.py        # Tesseract OCR + regex parsing
│   ├── llm/
│   │   ├── groq_client.py      # Groq API wrapper
│   │   └── prompts.py          # Prompt templates
│   ├── nutrition/
│   │   ├── models.py           # Dataclasses
│   │   ├── fda_guidelines.py   # DV% computation
│   │   └── usda_client.py      # USDA API client
│   ├── vision/
│   │   └── food_identifier.py  # Groq Vision API food recognition
│   ├── resources/
│   │   └── locator.py          # Free food resource finder (food banks, pantries, etc.)
│   └── ui/
│       ├── components.py       # Reusable Streamlit widgets
│       ├── pages_upload.py     # Image upload tab
│       ├── pages_snap.py       # Snap Food photo tab
│       ├── pages_manual.py     # Manual entry tab
│       ├── pages_recipe.py     # Recipe Generator tab
│       ├── pages_find.py       # Find Free Food Near You tab
│       └── pages_results.py    # Results display
├── data/
│   └── fda_daily_values.json   # FDA daily reference values
├── tests/
│   ├── test_ocr.py
│   ├── test_llm.py
│   ├── test_nutrition.py
│   └── sample_labels/
└── eval/
    ├── ocr_accuracy.py
    └── ground_truth.json
```

## Key Packages
```
streamlit>=1.30.0
opencv-python-headless>=4.8.0
pytesseract>=0.3.10
Pillow>=10.0.0
groq>=0.4.0
requests>=2.31.0
python-dotenv>=1.0.0
pytest>=7.4.0
```
System dependency: `brew install tesseract` (macOS) / `apt install tesseract-ocr` (Ubuntu)

---

### Phase 1 — Project Setup `March 31 – April 1`
> Goal: Get a running Streamlit skeleton with all dependencies installed.

- [x] **1.1 Scaffolding**
  - [x] 1.1.1 Create directory structure (all folders and `__init__.py` files)
  - [x] 1.1.2 Create `requirements.txt` with all packages listed above
  - [x] 1.1.3 Create `.gitignore` (include `.env`, `__pycache__/`, `.venv/`, `*.pyc`)
  - [x] 1.1.4 Create `.env.example` with `GROQ_API_KEY=` and `USDA_API_KEY=`
  - [x] 1.1.5 Set up virtual environment and install dependencies
  - [x] 1.1.6 Install Tesseract OCR system dependency

- [x] **1.2 Minimal Streamlit App**
  - [x] 1.2.1 Create `app.py` with page config (`st.set_page_config(page_title="NutriScan", layout="wide")`)
  - [x] 1.2.2 Add title, sidebar placeholder, and three tabs ("Upload Label", "Snap Food", "Manual Entry")
  - [x] 1.2.3 Verify `streamlit run app.py` launches in browser

- [x] **1.3 Git Init**
  - [x] 1.3.1 Initialize git repo
  - [x] 1.3.2 Create initial commit with scaffolding
  - [x] 1.3.3 Push to GitHub (confirm `.env` is not included)

---

### Phase 2 — Data Models + FDA Reference `April 1 – April 2`
> Goal: Build the data backbone that every other module depends on.

- [x] **2.1 Dataclasses** (`src/nutrition/models.py`)
  - [x] 2.1.1 Define `NutritionData` — calories, total_fat, saturated_fat, trans_fat, cholesterol, sodium, total_carbs, dietary_fiber, total_sugars, added_sugars, protein, vitamin_d, calcium, iron, potassium, serving_size, servings_per_container, ingredients_list
  - [x] 2.1.2 Define `HealthProfile` — caloric_target, dietary_goals (list[str]), allergens (list[str]), restrictions (list[str])
  - [x] 2.1.3 Define `AnalysisResult` — allergen_flags, preservative_flags, nutrient_flags, goal_alignment, recommendations, overall_risk, summary

- [x] **2.2 FDA Daily Values** (`data/fda_daily_values.json`)
  - [x] 2.2.1 Create JSON file with FDA 2,000-calorie daily reference values for all nutrients
  - [x] 2.2.2 Source values from FDA.gov (public data)

- [x] **2.3 DV% Computation** (`src/nutrition/fda_guidelines.py`)
  - [x] 2.3.1 Write `load_fda_values()` to read the JSON file
  - [x] 2.3.2 Write `compute_dv_percentages(nutrition_data: NutritionData) -> dict`
  - [x] 2.3.3 Test manually: 20g total fat → ~26% DV (based on 78g reference)

---

### Phase 3 — Core Features — Parallel Tracks `April 2 – April 7`
> Goal: Build the three independent subsystems. Aarav, Neil, and Nuv each take one track.

- [ ] **3.1 OCR Pipeline (Track A — Neil)**

  - [ ] **3.1.1 Image Preprocessing** (`src/ocr/preprocessor.py`)
    - [ ] 3.1.1.1 Accept PIL Image or file path as input
    - [ ] 3.1.1.2 Convert to grayscale
    - [ ] 3.1.1.3 Resize if image is too small (< 300 DPI equivalent)
    - [ ] 3.1.1.4 Apply adaptive thresholding (`cv2.adaptiveThreshold` with `ADAPTIVE_THRESH_GAUSSIAN_C`)
    - [ ] 3.1.1.5 Apply Gaussian blur to reduce noise
    - [ ] 3.1.1.6 Return processed image as numpy array

  - [ ] **3.1.2 OCR Extraction** (`src/ocr/extractor.py`)
    - [ ] 3.1.2.1 Call `preprocessor.preprocess(image)` to get cleaned image
    - [ ] 3.1.2.2 Run `pytesseract.image_to_string()` with config `--psm 6`
    - [ ] 3.1.2.3 Build regex patterns for each nutrient field (e.g. `r"total\s*fat\s*(\d+\.?\d*)\s*g"`)
    - [ ] 3.1.2.4 Parse ingredients list (find "Ingredients:" line, capture until next section)
    - [ ] 3.1.2.5 Return parsed `NutritionData` object + raw OCR text (for debugging)
    - [ ] 3.1.2.6 Add confidence indicator — count parsed fields out of ~15; warn if < 5

  - [ ] **3.1.3 OCR Testing**
    - [ ] 3.1.3.1 Collect 3-4 sample nutrition label photos
    - [ ] 3.1.3.2 Print raw Tesseract output to understand actual text before writing regex
    - [ ] 3.1.3.3 Write unit tests in `tests/test_ocr.py` with hardcoded strings
    - [ ] 3.1.3.4 Test edge cases: missing fields, "8 g" vs "8g", decimal values

- [ ] **3.2 LLM Integration (Track B — Aarav)**

  - [x] **3.2.1 Prompt Templates** (`src/llm/prompts.py`)
    - [x] 3.2.1.1 Write system prompt with JSON output schema (allergen detection, preservative flagging, sugar/nutrient flags, goal alignment, recommendations)
    - [x] 3.2.1.2 Define JSON response structure: `allergen_flags`, `preservative_flags`, `nutrient_flags`, `goal_alignment`, `recommendations`, `overall_risk`, `summary`
    - [x] 3.2.1.3 Write user prompt template that fills in nutrition data + DV% + ingredients + health profile

  - [x] **3.2.2 Groq API Client** (`src/llm/groq_client.py`)
    - [x] 3.2.2.1 Load API key from environment variable via `python-dotenv`
    - [x] 3.2.2.2 Initialize Groq client
    - [x] 3.2.2.3 Write `analyze(nutrition_data, health_profile, dv_percentages) -> AnalysisResult`
    - [x] 3.2.2.4 Use `response_format={"type": "json_object"}` to force JSON output
    - [x] 3.2.2.5 Set `temperature=0.3` for factual consistency
    - [x] 3.2.2.6 Parse JSON response into `AnalysisResult` dataclass
    - [x] 3.2.2.7 Add try/except with retry on rate limit (30 RPM, 1K req/day)
    - [x] 3.2.2.8 Show user-friendly error via `st.error()` on failure

  - [ ] **3.2.3 LLM Testing**
    - [ ] 3.2.3.1 Write unit tests in `tests/test_llm.py` for prompt construction
    - [ ] 3.2.3.2 Test response parsing with mock JSON → verify `AnalysisResult`
    - [ ] 3.2.3.3 Manual test: call Groq API with sample data, inspect output

- [ ] **3.3 USDA API + Streamlit UI (Track C — Nuv)**

  - [ ] **3.3.1 USDA Client** (`src/nutrition/usda_client.py`)
    - [ ] 3.3.1.1 Register for free API key at api.data.gov
    - [ ] 3.3.1.2 Write `search_food(query, api_key) -> dict` calling `/fdc/v1/foods/search`
    - [ ] 3.3.1.3 Write `check_preservatives(ingredients_list) -> list[str]` with hardcoded preservative list
    - [ ] 3.3.1.4 Cache results in `st.session_state`

  - [x] **3.3.2 Health Profile Form** (`src/ui/components.py`)
    - [x] 3.3.2.1 Write `health_profile_form()` for the sidebar (caloric target, allergens multiselect, dietary goals, restrictions)
    - [x] 3.3.2.2 Store profile in `st.session_state`, return `HealthProfile` object

  - [x] **3.3.3 Nutrition Editor** (`src/ui/components.py`)
    - [x] 3.3.3.1 Write `nutrition_editor(nutrition_data)` — editable form pre-filled with OCR data
    - [x] 3.3.3.2 Each nutrient field is an `st.number_input`
    - [x] 3.3.3.3 Text area for ingredients list
    - [x] 3.3.3.4 Return corrected `NutritionData` on submit

  - [x] **3.3.4 Results Display** (`src/ui/pages_results.py`)
    - [x] 3.3.4.1 Write `results_display(result, dv_percentages)`
    - [x] 3.3.4.2 Colored flags: red for allergens/high risk, yellow for moderate, green for good
    - [x] 3.3.4.3 Bar chart of DV%
    - [x] 3.3.4.4 Recommendations as formatted text
    - [x] 3.3.4.5 Overall summary and risk level

  - [ ] **3.3.5 Upload Page** (`src/ui/pages_upload.py`)
    - [ ] 3.3.5.1 `st.file_uploader` accepting jpg/jpeg/png
    - [ ] 3.3.5.2 Display uploaded image
    - [ ] 3.3.5.3 Run OCR on upload, show raw text in expander
    - [ ] 3.3.5.4 Show parsed data in editable `nutrition_editor`
    - [ ] 3.3.5.5 "Analyze" button triggers LLM analysis

  - [ ] **3.3.6 Manual Entry Page** (`src/ui/pages_manual.py`)
    - [ ] 3.3.6.1 Render `nutrition_editor` with empty/zero defaults
    - [ ] 3.3.6.2 Include text area for ingredients list
    - [ ] 3.3.6.3 "Analyze" button triggers LLM analysis

- [ ] **3.4 Food Photo Recognition (Track D — Aarav)**
  > Upload a photo of actual food (not a label) → AI identifies items + portions → pulls nutrition data from USDA → feeds into existing analysis pipeline.

  - [ ] **3.4.1 Vision Prompt** (`src/llm/prompts.py`)
    - [ ] 3.4.1.1 Write vision system prompt that instructs the model to identify food items, estimate portions (in grams), and return structured JSON
    - [ ] 3.4.1.2 Define JSON response structure: `foods` array with `name`, `estimated_grams`, `confidence` per item
    - [ ] 3.4.1.3 Include instruction to be conservative on portions and flag uncertainty

  - [ ] **3.4.2 Food Identifier** (`src/vision/food_identifier.py`)
    - [ ] 3.4.2.1 Write `identify_food(image_bytes) -> list[dict]` using Groq with `llama-3.2-90b-vision-preview`
    - [ ] 3.4.2.2 Encode image to base64, send as image content in chat completion
    - [ ] 3.4.2.3 Parse JSON response into list of identified food items
    - [ ] 3.4.2.4 Add try/except with user-friendly error on failure

  - [ ] **3.4.3 USDA Bridge** (`src/vision/food_identifier.py`)
    - [ ] 3.4.3.1 Write `lookup_food_nutrition(food_name, grams, usda_client) -> NutritionData` — search USDA for the food, scale nutrition values to estimated portion
    - [ ] 3.4.3.2 Write `aggregate_nutrition(food_items) -> NutritionData` — combine multiple foods into one `NutritionData` for analysis
    - [ ] 3.4.3.3 Handle USDA miss gracefully — if food not found, flag it to the user

  - [ ] **3.4.4 Snap Food Page** (`src/ui/pages_snap.py`)
    - [ ] 3.4.4.1 `st.file_uploader` or `st.camera_input` for food photo
    - [ ] 3.4.4.2 Display uploaded photo
    - [ ] 3.4.4.3 "Identify Food" button → call vision model → show identified items + portions
    - [ ] 3.4.4.4 Show editable table of identified foods (user can correct names/portions)
    - [ ] 3.4.4.5 "Get Nutrition & Analyze" button → USDA lookup → populate `nutrition_editor` → LLM analysis
    - [ ] 3.4.4.6 Show disclaimer: "Portions are AI-estimated — adjust if needed for accuracy"

  - [ ] **3.4.5 Vision Testing**
    - [ ] 3.4.5.1 Manual test: photo of simple meal (e.g. apple, sandwich) → check identified items
    - [ ] 3.4.5.2 Manual test: photo of complex plate → verify reasonable portion estimates
    - [ ] 3.4.5.3 Test USDA bridge with known foods → verify nutrition values are reasonable

---

### Phase 3.5 — Recipe Generator `April 9 – April 11`
> Goal: Add a 4th tab that lets users build a pantry from scanned labels or food photos, then generates a nutritious recipe. Combats food insecurity angle for the symposium.

- [x] **3.5.1 Data Models** (`src/nutrition/models.py`)
  - [x] 3.5.1.1 Add `PantryItem` dataclass — name, source, nutrition, estimated_grams, quantity
  - [x] 3.5.1.2 Add `GeneratedRecipe` dataclass — title, servings, ingredients_used, additional_ingredients_needed, instructions, estimated_nutrition, nutrition_highlights, tips

- [x] **3.5.2 Recipe Prompt Templates** (`src/llm/prompts.py`)
  - [x] 3.5.2.1 Write `build_recipe_system_prompt()` — nutritionist+chef persona, JSON output schema
  - [x] 3.5.2.2 Write `build_recipe_user_prompt(pantry_items, health_profile)` — lists ingredients + health profile

- [x] **3.5.3 Groq Recipe Generation** (`src/llm/groq_client.py`)
  - [x] 3.5.3.1 Write `GroqClient` class with `_call_with_retry()` and retry on rate limit
  - [x] 3.5.3.2 Write `generate_recipe(pantry_items, health_profile) -> GeneratedRecipe`
  - [x] 3.5.3.3 Parse JSON response into `GeneratedRecipe` with `NutritionData` for estimated nutrition

- [x] **3.5.4 Recipe Generator Tab UI** (`src/ui/pages_recipe.py`)
  - [x] 3.5.4.1 Pantry builder — label scan column + food photo column + manual add expander
  - [x] 3.5.4.2 Pantry display — item list with remove buttons + clear all
  - [x] 3.5.4.3 Recipe generation — generate/regenerate buttons, recipe display with instructions
  - [x] 3.5.4.4 Nutrition breakdown — DV% bar chart using `compute_dv_percentages`
  - [x] 3.5.4.5 Nutrition highlights, tips, and AI disclaimer

- [x] **3.5.5 Wire Up in app.py**
  - [x] 3.5.5.1 Add 4th tab "Recipe Generator" and import `render_recipe_tab()`

---

### Phase 4 — Integration `April 7 – April 9`
> Goal: Wire the three tracks together into one working app.

- [ ] **4.1 Wire Up the Pipeline**
  - [ ] 4.1.1 Connect upload page → OCR pipeline → editable form → LLM analysis → results display
  - [ ] 4.1.2 Connect manual entry page → LLM analysis → results display
  - [ ] 4.1.3 Connect snap food page → vision model → USDA lookup → editable form → LLM analysis → results display
  - [ ] 4.1.4 Ensure health profile sidebar feeds into all three flows

- [ ] **4.2 UX Flow Verification**
  - [ ] 4.2.1 Upload a clear photo → verify OCR extracts → edit → confirm → see results
  - [ ] 4.2.2 Manual entry → fill form → see results
  - [ ] 4.2.3 Snap food photo → verify identified items → adjust → see results
  - [ ] 4.2.4 Change health profile → re-analyze → verify recommendations change

- [ ] **4.3 Error Handling**
  - [ ] 4.3.1 Blurry/bad image → show warning + suggest manual entry
  - [ ] 4.3.2 Groq API failure → show `st.error()` with message
  - [ ] 4.3.3 USDA API failure → gracefully skip, don't crash
  - [ ] 4.3.4 Missing health profile fields → still works with generic analysis

---

### Phase 5 — Evaluation `April 9 – April 12`
> Goal: Get concrete accuracy numbers for the presentation.

- [ ] **5.1 OCR Evaluation**
  - [ ] 5.1.1 Collect 5-10 diverse nutrition label photos (different brands, lighting, angles)
  - [ ] 5.1.2 Hand-label ground truth in `eval/ground_truth.json`
  - [ ] 5.1.3 Write `eval/ocr_accuracy.py` to run OCR and compare to ground truth
  - [ ] 5.1.4 Compute metrics: field extraction rate + field accuracy (±1 tolerance)
  - [ ] 5.1.5 Record results for poster/presentation

- [ ] **5.2 LLM Evaluation**
  - [ ] 5.2.1 Create 5 test cases (nutrition label + health profile combos)
  - [ ] 5.2.2 Run each through the LLM pipeline
  - [ ] 5.2.3 Score pass/fail: allergen detection, nutrient flagging, preservative ID, recommendation relevance
  - [ ] 5.2.4 Record results for poster/presentation

---

### Phase 6 — Local Resource Finder `April 12 – April 14`
> Goal: Analyze the user's diet for nutrient gaps, then connect them to free or low-income-accessible food resources nearby. Focus exclusively on places that serve food-insecure households — no regular grocery stores or paid services.

- [ ] **6.1 Nutrient Gap Analysis**
  - [ ] 6.1.1 Compare user's scanned/entered foods against FDA daily values to identify deficiencies
  - [ ] 6.1.2 Generate a "missing nutrients" summary (e.g., "Low on iron, calcium, Vitamin D")
  - [ ] 6.1.3 Map deficiencies to food categories (leafy greens, dairy, legumes, etc.)

- [ ] **6.2 Local Resource Lookup**
  - [ ] 6.2.1 Research free APIs for low-income food access (USDA Food Desert Atlas, FoodFinder API, Feeding America locator, 211.org)
  - [ ] 6.2.2 Write `find_local_resources(zip_code, resource_type) -> list[dict]` — returns nearby free/low-cost places with name, address, hours, eligibility
  - [ ] 6.2.3 Resource types: food banks, food pantries, community fridges, free community gardens, SNAP/WIC retailers, free meal programs, subsidized farmers markets
  - [ ] 6.2.4 Filter out regular grocery stores and paid services — only free or income-qualified resources
  - [ ] 6.2.5 Fallback: curated list of West Lafayette / Lafayette free food resources (food banks, Purdue food pantry, community gardens) for video

- [ ] **6.3 LLM Recommendation Layer**
  - [ ] 6.3.1 Write prompt: given nutrient gaps + nearby free resources → personalized advice ("You're low on iron — the Lafayette Community Food Bank on Main St has free produce distributions on Saturdays")
  - [ ] 6.3.2 Frame around free/low-cost access: food bank hours, SNAP-eligible stores, free meal schedules, community garden sign-ups

- [ ] **6.4 UI — "Find Free Food Near You" Tab**
  - [ ] 6.4.1 Zip code / location input
  - [ ] 6.4.2 Display nutrient gap summary
  - [ ] 6.4.3 List of free/low-cost food resources with hours, address, and eligibility info
  - [ ] 6.4.4 Personalized LLM advice connecting nutrient gaps to specific free resources

---

### Phase 7 — Presentation + Video `April 14 – April 16`
> Goal: Research talk with recorded video walkthrough of the app. No live demo needed.

- [ ] **7.1 App Polish**
  - [ ] 7.1.1 Clean up Streamlit styling (page title, icon, colors)
  - [ ] 7.1.2 Add brief app description/instructions on main page
  - [ ] 7.1.3 Final error handling pass — no tracebacks during video recording

- [ ] **7.2 Video Walkthrough Scenarios**
  - [ ] 7.2.1 Scenario 1: Upload a clear label photo with no health concerns → basic analysis
  - [ ] 7.2.2 Scenario 2: Upload label with peanut-allergic profile → allergen flagging
  - [ ] 7.2.3 Scenario 3: Manual entry of high-sodium product with "low sodium" goal → goal mismatch
  - [ ] 7.2.4 Scenario 4: Product with preservatives → preservative warnings
  - [ ] 7.2.5 Scenario 5: Snap photo of a meal → AI identifies foods → nutrition breakdown + analysis
  - [ ] 7.2.6 Scenario 6: Recipe from scanned labels (cereal, beans, milk, bread) with "high protein" goal
  - [ ] 7.2.7 Scenario 7: Food insecurity — recipe from rice, canned beans, onion → maximize nutrition
  - [ ] 7.2.8 Scenario 8: Nutrient gap analysis → local resource recommendations
  - [ ] 7.2.9 Scenario 9: Allergen-safe recipe — peanut+dairy allergens set, verify recipe excludes them

- [ ] **7.3 Record Video**
  - [ ] 7.3.1 Run through all scenarios in the app, screen record each
  - [ ] 7.3.2 Edit into a cohesive walkthrough video (2-4 minutes)
  - [ ] 7.3.3 Add voiceover or captions explaining each feature

- [ ] **7.4 Presentation Slides**
  - [ ] 7.4.1 Problem statement — food insecurity + nutrition literacy gap
  - [ ] 7.4.2 Solution overview — NutriScan's 5 features (label scan, food snap, manual entry, recipe generator, free local resources)
  - [ ] 7.4.3 Technical architecture slide (OCR, Groq LLM, USDA API, Vision)
  - [ ] 7.4.4 Evaluation results (OCR accuracy, LLM checklist scores)
  - [ ] 7.4.5 Embed or link video walkthrough
  - [ ] 7.4.6 Future work — expanded local resources, multi-language support, mobile app
  - [ ] 7.4.7 Practice talk (aim for ~10 min depending on symposium format)

- [ ] **7.5 Day-of Checklist** `April 16`
  - [ ] 7.5.1 Slides exported/uploaded and accessible
  - [ ] 7.5.2 Video plays correctly from slides
  - [ ] 7.5.3 Backup: have app running on laptop in case of Q&A ("can you show me X?")

---

## Suggested Task Division (~33% each, build work only)

| Person | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|--------|---------|---------|---------|---------|
| **Aarav** | 3.2 LLM Integration + 3.4 Vision (minus Snap UI) + 3.5 Recipe (done) | Integration lead — wires all tracks together | 5.2 LLM eval | — |
| **Neil** | 3.1 OCR Pipeline | Integrates own OCR track | 5.1 OCR eval | 6.1-6.3 Local Resources backend (gap analysis, resource lookup, LLM recs) |
| **Nuv** | 3.3 USDA + Streamlit UI + 3.4.4 Snap Food Page UI | Integrates own UI track | — | 6.4 Find Food Near You tab UI |

### Already Completed (Aarav)
- Phases 1-2: Project scaffolding, data models, FDA guidelines
- Phase 3.5: Recipe Generator feature (models, prompts, Groq client, UI, wiring)

---

## Verification Summary
- **Unit tests:** OCR parsing, DV% math, prompt construction, response parsing, recipe generation (`pytest tests/`)
- **Integration tests (manual):** Clear photo, blurry photo, food snap, allergen scenario, diet goal scenario, empty profile, recipe from pantry, free resource lookup
- **Evaluation:** OCR field accuracy on 5-10 images; LLM checklist on 5 test cases; vision food ID spot checks; recipe quality spot checks
- **Video recording:** Run all 9 walkthrough scenarios (Phase 7.2) and screen record before April 16
- **Pre-talk check:** Slides + video ready, app running as backup for Q&A
