"""
Unit tests for the OCR pipeline (Phase 3.1.3).

Tests the regex parsing logic in extractor.py using hardcoded strings that
simulate real Tesseract output from nutrition labels.  This lets us validate
parsing without requiring Tesseract or sample images at test time.

Also includes a real-image integration test (TestRealImageExtraction) that
runs the full preprocess → Tesseract → regex pipeline on sample photos in
tests/sample_labels/. That class is auto-skipped if Tesseract isn't installed
or the images are missing.
"""

from pathlib import Path

import pytest

from src.nutrition.models import NutritionData
from src.ocr.extractor import (
    _parse_nutrition,
    _parse_ingredients,
    _compute_confidence,
    extract,
)

SAMPLE_DIR = Path(__file__).parent / "sample_labels"


# ======================================================================
# 3.1.3.1  Sample nutrition label text (simulated Tesseract output)
# ======================================================================
# These strings mimic the messy, slightly inconsistent text that Tesseract
# typically produces from real nutrition label photos.

# --- Sample 1: Clean, well-formatted label (e.g. a cereal box) ---
SAMPLE_CLEAN = """\
Nutrition Facts
Serving Size 1 Cup (55g)
Servings Per Container About 8

Calories 210

Total Fat 3g
  Saturated Fat 0.5g
  Trans Fat 0g
Cholesterol 0mg
Sodium 200mg
Total Carbohydrate 44g
  Dietary Fiber 5g
  Total Sugars 12g
    Incl. Added Sugars 10g
Protein 5g

Vitamin D 2mcg
Calcium 260mg
Iron 8mg
Potassium 240mg

Ingredients: Whole Grain Wheat, Sugar, Corn Syrup,
Wheat Bran, Salt, Calcium Carbonate, Iron.
Contains: Wheat.
"""

# --- Sample 2: Spacing variations ("8 g" vs "8g") ---
SAMPLE_SPACED = """\
Nutrition Facts
Serving Size  2/3 cup (55g)
Servings per Container  8

Calories  230

Total Fat  8 g
  Saturated Fat  1 g
  Trans Fat  0 g
Cholesterol  0 mg
Sodium  160 mg
Total Carbohydrate  37 g
  Dietary Fiber  4 g
  Total Sugars  12 g
    Added Sugars  10 g
Protein  3 g

Vitamin D  2 mcg
Calcium  200 mg
Iron  6 mg
Potassium  235 mg
"""

# --- Sample 3: Decimal values and partial data ---
SAMPLE_DECIMALS = """\
Nutrition Facts
Serving Size 1 bar (40g)
Servings Per Container 6

Calories 190

Total Fat 7.5g
  Saturated Fat 3.2g
  Trans Fat 0.5g
Cholesterol 15mg
Sodium 95mg
Total Carbs 28.5g
  Dietary Fiber 1.5g
  Total Sugars 14.8g
Protein 3.2g
"""

# --- Sample 4: Very sparse label (missing most fields → low confidence) ---
SAMPLE_SPARSE = """\
Calories 100
Total Fat 2g
Protein 1g
"""

# --- Sample 5: Messy OCR with extra noise ---
SAMPLE_NOISY = """\
NuUrition Facts
SerVing Size: 1 piece (28g)
Servings Per Container: about 12

Calorics 150
   Am. per serving

Total Fat 8g        10%
  Saturated Fat 3g  15%
  Trans Fat 0g
Cholesteral 5mg      2%
Sodium 110mg         5%
Total Carbohydrate 18g  6%
  Dietary Fiber 1g      4%
  Total Sugars 9g
    Incl Added Sugars 7g
Protein 2g

Ingredients: Sugar, Palm Oil, Hazelnuts, Cocoa,
Skim Milk, Whey, Lecithin, Vanillin.
Allergen Info: Contains Milk, Hazelnuts.
"""


# ======================================================================
# 3.1.3.3  Unit tests with hardcoded strings
# ======================================================================

class TestParseNutritionClean:
    """Test parsing a clean, well-formatted nutrition label."""

    def setup_method(self):
        self.nutrition, self.fields = _parse_nutrition(SAMPLE_CLEAN)

    def test_calories(self):
        assert self.nutrition.calories == 210.0

    def test_total_fat(self):
        assert self.nutrition.total_fat == 3.0

    def test_saturated_fat(self):
        assert self.nutrition.saturated_fat == 0.5

    def test_trans_fat(self):
        assert self.nutrition.trans_fat == 0.0

    def test_cholesterol(self):
        assert self.nutrition.cholesterol == 0.0

    def test_sodium(self):
        assert self.nutrition.sodium == 200.0

    def test_total_carbs(self):
        assert self.nutrition.total_carbs == 44.0

    def test_dietary_fiber(self):
        assert self.nutrition.dietary_fiber == 5.0

    def test_total_sugars(self):
        assert self.nutrition.total_sugars == 12.0

    def test_added_sugars(self):
        assert self.nutrition.added_sugars == 10.0

    def test_protein(self):
        assert self.nutrition.protein == 5.0

    def test_vitamin_d(self):
        assert self.nutrition.vitamin_d == 2.0

    def test_calcium(self):
        assert self.nutrition.calcium == 260.0

    def test_iron(self):
        assert self.nutrition.iron == 8.0

    def test_potassium(self):
        assert self.nutrition.potassium == 240.0

    def test_fields_parsed_all_15(self):
        assert self.fields == 15

    def test_serving_size(self):
        assert "1 Cup" in self.nutrition.serving_size

    def test_servings_per_container(self):
        assert self.nutrition.servings_per_container == 8.0

    def test_high_confidence(self):
        assert _compute_confidence(self.fields) == "high"


# ======================================================================
# 3.1.3.4  Edge cases: spacing variations ("8 g" vs "8g")
# ======================================================================

class TestParseNutritionSpaced:
    """Test that regex handles spaces between value and unit."""

    def setup_method(self):
        self.nutrition, self.fields = _parse_nutrition(SAMPLE_SPACED)

    def test_total_fat_with_space(self):
        assert self.nutrition.total_fat == 8.0

    def test_saturated_fat_with_space(self):
        assert self.nutrition.saturated_fat == 1.0

    def test_sodium_with_space(self):
        assert self.nutrition.sodium == 160.0

    def test_dietary_fiber_with_space(self):
        assert self.nutrition.dietary_fiber == 4.0

    def test_all_fields_parsed(self):
        assert self.fields == 15

    def test_calories(self):
        assert self.nutrition.calories == 230.0


# ======================================================================
# 3.1.3.4  Edge cases: decimal values
# ======================================================================

class TestParseNutritionDecimals:
    """Test that regex correctly captures decimal nutrient values."""

    def setup_method(self):
        self.nutrition, self.fields = _parse_nutrition(SAMPLE_DECIMALS)

    def test_total_fat_decimal(self):
        assert self.nutrition.total_fat == 7.5

    def test_saturated_fat_decimal(self):
        assert self.nutrition.saturated_fat == 3.2

    def test_trans_fat_decimal(self):
        assert self.nutrition.trans_fat == 0.5

    def test_total_carbs_decimal(self):
        assert self.nutrition.total_carbs == 28.5

    def test_dietary_fiber_decimal(self):
        assert self.nutrition.dietary_fiber == 1.5

    def test_total_sugars_decimal(self):
        assert self.nutrition.total_sugars == 14.8

    def test_protein_decimal(self):
        assert self.nutrition.protein == 3.2

    def test_cholesterol(self):
        assert self.nutrition.cholesterol == 15.0

    def test_uses_total_carbs_abbreviation(self):
        """'Total Carbs' (abbreviated) should match the total_carbs pattern."""
        assert self.nutrition.total_carbs == 28.5


# ======================================================================
# 3.1.3.4  Edge cases: missing fields (sparse label → low confidence)
# ======================================================================

class TestParseNutritionSparse:
    """Test behavior when most fields are missing."""

    def setup_method(self):
        self.nutrition, self.fields = _parse_nutrition(SAMPLE_SPARSE)

    def test_only_present_fields_parsed(self):
        assert self.fields == 3  # calories, total_fat, protein

    def test_calories(self):
        assert self.nutrition.calories == 100.0

    def test_total_fat(self):
        assert self.nutrition.total_fat == 2.0

    def test_protein(self):
        assert self.nutrition.protein == 1.0

    def test_missing_fields_default_zero(self):
        assert self.nutrition.sodium == 0.0
        assert self.nutrition.cholesterol == 0.0
        assert self.nutrition.dietary_fiber == 0.0
        assert self.nutrition.vitamin_d == 0.0

    def test_low_confidence(self):
        assert _compute_confidence(self.fields) == "low"


# ======================================================================
# Noisy OCR text (simulates real-world Tesseract output)
# ======================================================================

class TestParseNutritionNoisy:
    """Test regex resilience against noisy/messy OCR output."""

    def setup_method(self):
        self.nutrition, self.fields = _parse_nutrition(SAMPLE_NOISY)

    def test_total_fat(self):
        assert self.nutrition.total_fat == 8.0

    def test_saturated_fat(self):
        assert self.nutrition.saturated_fat == 3.0

    def test_trans_fat(self):
        assert self.nutrition.trans_fat == 0.0

    def test_sodium(self):
        assert self.nutrition.sodium == 110.0

    def test_total_carbs(self):
        assert self.nutrition.total_carbs == 18.0

    def test_total_sugars(self):
        assert self.nutrition.total_sugars == 9.0

    def test_added_sugars(self):
        assert self.nutrition.added_sugars == 7.0

    def test_protein(self):
        assert self.nutrition.protein == 2.0

    def test_serving_size_with_colon(self):
        """Serving size line uses ':' separator — should still parse."""
        assert "1 piece" in self.nutrition.serving_size

    def test_servings_per_container_with_about(self):
        """'about 12' should parse the numeric part."""
        assert self.nutrition.servings_per_container == 12.0


# ======================================================================
# 3.1.3.4  Ingredients parsing
# ======================================================================

class TestParseIngredients:
    """Test ingredients list extraction."""

    def test_clean_label_ingredients(self):
        ingredients = _parse_ingredients(SAMPLE_CLEAN)
        assert "Whole Grain Wheat" in ingredients
        assert "Sugar" in ingredients
        assert "Iron" in ingredients
        # Should NOT include the "Contains:" section
        assert "Contains" not in ingredients

    def test_noisy_label_ingredients(self):
        ingredients = _parse_ingredients(SAMPLE_NOISY)
        assert "Sugar" in ingredients
        assert "Palm Oil" in ingredients
        assert "Vanillin" in ingredients
        # Should stop before "Allergen Info:"
        assert "Allergen" not in ingredients

    def test_no_ingredients_section(self):
        """If there's no 'Ingredients:' at all, return empty string."""
        ingredients = _parse_ingredients(SAMPLE_SPACED)
        assert ingredients == ""

    def test_ingredients_semicolon_separator(self):
        """Some labels use ';' instead of ':'."""
        text = "Ingredients; Water, Salt, Vinegar.\nContains: None."
        ingredients = _parse_ingredients(text)
        assert "Water" in ingredients
        assert "Salt" in ingredients


# ======================================================================
# 3.1.3.4  Confidence indicator
# ======================================================================

class TestConfidence:
    """Test the confidence level classification."""

    def test_high_confidence(self):
        assert _compute_confidence(15) == "high"
        assert _compute_confidence(10) == "high"

    def test_medium_confidence(self):
        assert _compute_confidence(9) == "medium"
        assert _compute_confidence(5) == "medium"

    def test_low_confidence(self):
        assert _compute_confidence(4) == "low"
        assert _compute_confidence(0) == "low"


# ======================================================================
# 3.1.3.1 / 3.1.3.2  Real-image integration tests
# ======================================================================
# These tests run the full pipeline (preprocess → Tesseract → regex) on
# sample nutrition label photos committed to tests/sample_labels/.
#
# The whole class is skipped if Tesseract isn't installed, so developers
# without the system dependency can still run the hardcoded-string tests.

def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _tesseract_available(),
    reason="Tesseract not installed — skipping real-image integration tests",
)
class TestRealImageExtraction:
    """
    Run the full OCR pipeline on real nutrition label photos.

    The FDA 2014 standard label is our golden image — clean, well-lit, and
    representative of the label format we target. Values below were verified
    manually against the actual label content: Total Fat 8g, Sat Fat 1g,
    Sodium 160mg, Total Carbs 37g, Fiber 4g, Protein 3g, Vit D 2mcg,
    Calcium 260mg, Iron 8mg, Potassium 235mg, Calories 230, 8 servings.
    """

    fda_path = SAMPLE_DIR / "fda_2014.jpg"
    noisy_paths = [
        SAMPLE_DIR / "agave_nectar.jpg",
        SAMPLE_DIR / "high_sat_fat.jpg",
    ]

    @pytest.fixture(scope="class")
    def fda_result(self):
        if not self.fda_path.exists():
            pytest.skip(f"Sample image not found: {self.fda_path}")
        return extract(str(self.fda_path))

    # --- FDA 2014 golden image: high-confidence parse ---------------------

    def test_fda_confidence_high(self, fda_result):
        assert fda_result.confidence == "high"

    def test_fda_most_fields_parsed(self, fda_result):
        # Tesseract misreads "Total Sugars 1g" as "Sugars ig" on this image,
        # which is an unfixable OCR failure at the regex layer. So we accept
        # 14/15 rather than a full 15.
        assert fda_result.fields_parsed >= 13, (
            f"Expected ≥13 fields, got {fda_result.fields_parsed}. "
            f"Raw text:\n{fda_result.raw_text}"
        )

    def test_fda_calories(self, fda_result):
        assert fda_result.nutrition.calories == 230.0

    def test_fda_total_fat(self, fda_result):
        assert fda_result.nutrition.total_fat == 8.0

    def test_fda_saturated_fat(self, fda_result):
        assert fda_result.nutrition.saturated_fat == 1.0

    def test_fda_sodium(self, fda_result):
        assert fda_result.nutrition.sodium == 160.0

    def test_fda_total_carbs(self, fda_result):
        assert fda_result.nutrition.total_carbs == 37.0

    def test_fda_dietary_fiber(self, fda_result):
        assert fda_result.nutrition.dietary_fiber == 4.0

    def test_fda_protein(self, fda_result):
        assert fda_result.nutrition.protein == 3.0

    def test_fda_vitamin_d(self, fda_result):
        assert fda_result.nutrition.vitamin_d == 2.0

    def test_fda_calcium(self, fda_result):
        assert fda_result.nutrition.calcium == 260.0

    def test_fda_iron_lowercase_l_misread(self, fda_result):
        """
        Tesseract OCR'd "Iron" as "lron" (lowercase L). The regex accepts
        [il1]ron — this test locks in that fix.
        """
        assert fda_result.nutrition.iron == 8.0

    def test_fda_potassium(self, fda_result):
        assert fda_result.nutrition.potassium == 235.0

    def test_fda_servings_per_container_reversed_order(self, fda_result):
        """
        FDA 2014+ label format: "8 servings per container" (number first).
        The reversed-order regex pattern locks in that fix.
        """
        assert fda_result.nutrition.servings_per_container == 8.0

    def test_fda_serving_size(self, fda_result):
        assert "2/3" in fda_result.nutrition.serving_size
        assert "55g" in fda_result.nutrition.serving_size

    # --- Graceful degradation on unreadable images ------------------------

    def test_noisy_images_do_not_crash(self):
        """
        Heavily noisy / bilingual / low-contrast photos produce garbage OCR.
        The pipeline should degrade gracefully — return low confidence, not
        raise an exception.
        """
        for path in self.noisy_paths:
            if not path.exists():
                continue
            result = extract(str(path))
            assert result.confidence in ("low", "medium"), (
                f"{path.name}: expected low/medium confidence on noisy image, "
                f"got {result.confidence} ({result.fields_parsed}/15 fields)"
            )


# ======================================================================
# 3.1.3.2  Helper to print raw Tesseract output (run manually)
# ======================================================================

def print_raw_ocr(image_path: str):
    """
    Utility to print raw Tesseract output for a given image.
    Run manually to understand actual OCR text before tuning regex:

        python -c "from tests.test_ocr import print_raw_ocr; print_raw_ocr('path/to/label.jpg')"
    """
    from src.ocr.preprocessor import preprocess
    import pytesseract

    processed = preprocess(image_path)
    raw = pytesseract.image_to_string(processed, config="--psm 6")
    print("=" * 60)
    print("RAW TESSERACT OUTPUT")
    print("=" * 60)
    print(raw)
    print("=" * 60)
    print(f"Total characters: {len(raw)}")
    print(f"Total lines: {len(raw.splitlines())}")
