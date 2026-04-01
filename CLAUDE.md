# NutriScan Build Plan

## Context
NutriScan is an AI-powered food nutrition label analyzer for personalized dietary insights, being built by 3 Purdue freshmen (Aarav, Neil, Nuv) through Dataception for the undergraduate research symposium on **April 16, 2026**. All-free tech stack.

## Tech Stack
- **Python** + **Streamlit** (pure Python frontend)
- **Tesseract** via `pytesseract` + **OpenCV** for OCR
- **Groq API** with Llama 3.3-70b-versatile (free tier)
- **USDA FoodData Central API** (free key from api.data.gov)
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
│   └── ui/
│       ├── components.py       # Reusable Streamlit widgets
│       ├── pages_upload.py     # Image upload tab
│       ├── pages_manual.py     # Manual entry tab
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
  - [x] 1.2.2 Add title, sidebar placeholder, and two tabs ("Upload Label", "Manual Entry")
  - [x] 1.2.3 Verify `streamlit run app.py` launches in browser

- [x] **1.3 Git Init**
  - [x] 1.3.1 Initialize git repo
  - [x] 1.3.2 Create initial commit with scaffolding
  - [x] 1.3.3 Push to GitHub (confirm `.env` is not included)

---

### Phase 2 — Data Models + FDA Reference `April 1 – April 2`
> Goal: Build the data backbone that every other module depends on.

- [ ] **2.1 Dataclasses** (`src/nutrition/models.py`)
  - [ ] 2.1.1 Define `NutritionData` — calories, total_fat, saturated_fat, trans_fat, cholesterol, sodium, total_carbs, dietary_fiber, total_sugars, added_sugars, protein, vitamin_d, calcium, iron, potassium, serving_size, servings_per_container, ingredients_list
  - [ ] 2.1.2 Define `HealthProfile` — caloric_target, dietary_goals (list[str]), allergens (list[str]), restrictions (list[str])
  - [ ] 2.1.3 Define `AnalysisResult` — allergen_flags, preservative_flags, nutrient_flags, goal_alignment, recommendations, overall_risk, summary

- [ ] **2.2 FDA Daily Values** (`data/fda_daily_values.json`)
  - [ ] 2.2.1 Create JSON file with FDA 2,000-calorie daily reference values for all nutrients
  - [ ] 2.2.2 Source values from FDA.gov (public data)

- [ ] **2.3 DV% Computation** (`src/nutrition/fda_guidelines.py`)
  - [ ] 2.3.1 Write `load_fda_values()` to read the JSON file
  - [ ] 2.3.2 Write `compute_dv_percentages(nutrition_data: NutritionData) -> dict`
  - [ ] 2.3.3 Test manually: 20g total fat → ~26% DV (based on 78g reference)

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

  - [ ] **3.2.1 Prompt Templates** (`src/llm/prompts.py`)
    - [ ] 3.2.1.1 Write system prompt with JSON output schema (allergen detection, preservative flagging, sugar/nutrient flags, goal alignment, recommendations)
    - [ ] 3.2.1.2 Define JSON response structure: `allergen_flags`, `preservative_flags`, `nutrient_flags`, `goal_alignment`, `recommendations`, `overall_risk`, `summary`
    - [ ] 3.2.1.3 Write user prompt template that fills in nutrition data + DV% + ingredients + health profile

  - [ ] **3.2.2 Groq API Client** (`src/llm/groq_client.py`)
    - [ ] 3.2.2.1 Load API key from environment variable via `python-dotenv`
    - [ ] 3.2.2.2 Initialize Groq client
    - [ ] 3.2.2.3 Write `analyze(nutrition_data, health_profile, dv_percentages) -> AnalysisResult`
    - [ ] 3.2.2.4 Use `response_format={"type": "json_object"}` to force JSON output
    - [ ] 3.2.2.5 Set `temperature=0.3` for factual consistency
    - [ ] 3.2.2.6 Parse JSON response into `AnalysisResult` dataclass
    - [ ] 3.2.2.7 Add try/except with retry on rate limit (30 RPM, 1K req/day)
    - [ ] 3.2.2.8 Show user-friendly error via `st.error()` on failure

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

  - [ ] **3.3.2 Health Profile Form** (`src/ui/components.py`)
    - [ ] 3.3.2.1 Write `health_profile_form()` for the sidebar (caloric target, allergens multiselect, dietary goals, restrictions)
    - [ ] 3.3.2.2 Store profile in `st.session_state`, return `HealthProfile` object

  - [ ] **3.3.3 Nutrition Editor** (`src/ui/components.py`)
    - [ ] 3.3.3.1 Write `nutrition_editor(nutrition_data)` — editable form pre-filled with OCR data
    - [ ] 3.3.3.2 Each nutrient field is an `st.number_input`
    - [ ] 3.3.3.3 Text area for ingredients list
    - [ ] 3.3.3.4 Return corrected `NutritionData` on submit

  - [ ] **3.3.4 Results Display** (`src/ui/pages_results.py`)
    - [ ] 3.3.4.1 Write `results_display(result, dv_percentages)`
    - [ ] 3.3.4.2 Colored flags: red for allergens/high risk, yellow for moderate, green for good
    - [ ] 3.3.4.3 Bar chart of DV%
    - [ ] 3.3.4.4 Recommendations as formatted text
    - [ ] 3.3.4.5 Overall summary and risk level

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

---

### Phase 4 — Integration `April 7 – April 9`
> Goal: Wire the three tracks together into one working app.

- [ ] **4.1 Wire Up the Pipeline**
  - [ ] 4.1.1 Connect upload page → OCR pipeline → editable form → LLM analysis → results display
  - [ ] 4.1.2 Connect manual entry page → LLM analysis → results display
  - [ ] 4.1.3 Ensure health profile sidebar feeds into both flows

- [ ] **4.2 UX Flow Verification**
  - [ ] 4.2.1 Upload a clear photo → verify OCR extracts → edit → confirm → see results
  - [ ] 4.2.2 Manual entry → fill form → see results
  - [ ] 4.2.3 Change health profile → re-analyze → verify recommendations change

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

### Phase 6 — Polish + Demo Prep `April 12 – April 16`
> Goal: App looks clean, demo is rehearsed, ready to present.

- [ ] **6.1 App Polish**
  - [ ] 6.1.1 Clean up Streamlit styling (page title, icon, colors)
  - [ ] 6.1.2 Add brief app description/instructions on main page
  - [ ] 6.1.3 Final error handling pass — no tracebacks during demo

- [ ] **6.2 Demo Scenarios**
  - [ ] 6.2.1 Scenario 1: Upload a clear label photo with no health concerns → basic analysis
  - [ ] 6.2.2 Scenario 2: Upload label with peanut-allergic profile → allergen flagging
  - [ ] 6.2.3 Scenario 3: Manual entry of high-sodium product with "low sodium" goal → goal mismatch
  - [ ] 6.2.4 Scenario 4: Product with preservatives → preservative warnings

- [ ] **6.3 Presentation Materials**
  - [ ] 6.3.1 Screenshots of app for poster/slides
  - [ ] 6.3.2 Write up evaluation results
  - [ ] 6.3.3 Prepare talking points for each demo scenario
  - [ ] 6.3.4 Practice demo run-through

- [ ] **6.4 Day-of Checklist** `April 16`
  - [ ] 6.4.1 Verify `.env` has valid API keys on demo laptop
  - [ ] 6.4.2 Run all demo scenarios — confirm no crashes
  - [ ] 6.4.3 Have manual entry as backup if OCR/image upload has issues
  - [ ] 6.4.4 Keep phone charged for taking live label photos (if doing live demo)

---

## Suggested Task Division

| Person | Phase 3 Track | Other Phases |
|--------|--------------|--------------|
| Aarav  | 3.2 LLM Integration | Phases 1-2 setup, Phase 4 integration, presentation lead |
| Neil   | 3.1 OCR Pipeline | Phase 5.1 OCR evaluation |
| Nuv    | 3.3 USDA + Streamlit UI | Phase 5.2 LLM evaluation, Phase 6 polish |

*All three collaborate on Phase 4 (integration) and Phase 6 (demo prep).*

---

## Verification Summary
- **Unit tests:** OCR parsing, DV% math, prompt construction, response parsing (`pytest tests/`)
- **Integration tests (manual):** Clear photo, blurry photo, allergen scenario, diet goal scenario, empty profile
- **Evaluation:** OCR field accuracy on 5-10 images; LLM checklist on 5 test cases
- **Demo smoke test:** Run all 4 demo scenarios morning of April 16
