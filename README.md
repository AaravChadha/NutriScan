<p align="center">
  <h1 align="center">NutriScan</h1>
  <p align="center">
    <strong>AI-Powered Nutrition Assistant for Combating Food Insecurity</strong>
  </p>
</p>

---

NutriScan reads nutrition labels, identifies food from photos, generates nutritious recipes from available ingredients, and connects users to free food resources nearby. Every API in the stack is free — designed to be accessible to anyone.

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

Built by three Purdue University freshmen through [Dataception](https://dataception.org):

| Member | Contributions |
|--------|--------------|
| **Aarav Chadha** | Project planning and architecture. Scaffolding, data models, FDA daily values. LLM integration (prompts, Groq client, analysis pipeline). Food photo recognition (vision prompts, Groq vision client, USDA/OFF bridge). Recipe generator. Vision-based label reader replacing OCR on golden path. Pipeline wire-up, UX verification, error handling. LLM evaluation (29/30, 96.7%). Dark mode theme polish, scroll fix, toast notifications. |
| **Neil Sachdev** | OCR pipeline (image preprocessor, Tesseract extractor, regex patterns). Unit tests for OCR parsing. Nutrient gap analysis against FDA daily values. Local resource lookup with curated Lafayette/West Lafayette database (11 free food resources). LLM recommendation layer connecting nutrient gaps to nearby resources. |
| **Nuv Ahuja** | USDA API client and preservative checker. Health profile sidebar form. Nutrition editor widget. Results display (colored flags, DV% chart, recommendations). Upload Label, Manual Entry, and Snap Food page scaffolds. Tab wiring. Find Free Food tab UI. Comprehensive UI overhaul (CSS theme, grade badges, styled cards, recipe layout). |

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
│   └── sample_labels/              # Test nutrition label photos
└── eval/
    ├── llm_accuracy.py             # Evaluation runner + scorer
    └── llm_accuracy_report.md      # Results: 29/30 (96.7%)
```

## Evaluation

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
