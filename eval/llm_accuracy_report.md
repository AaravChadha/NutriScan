# Phase 5.1 — LLM Evaluation Results

**Overall:** 29/30 checks passed (**96.7%**) across 5 test cases.

Scoring is substring-based and case-insensitive — we test whether the LLM captures each concept, not whether it matches exact wording, because Groq phrases things differently across temperature=0.3 runs.

## Per-dimension pass rate

| Dimension | Passed | Total | Rate |
|---|---|---|---|
| allergen | 2 | 2 | 100.0% |
| forbidden_allergen | 4 | 4 | 100.0% |
| forbidden_preservative | 3 | 3 | 100.0% |
| goal | 2 | 2 | 100.0% |
| min_recs | 5 | 5 | 100.0% |
| nutrient | 4 | 4 | 100.0% |
| preservative | 5 | 5 | 100.0% |
| risk | 4 | 5 | 80.0% |

## Per-case summary

| Case | Passed | Risk | Status |
|---|---|---|---|
| `1_clean_pass_oats` | 9/9 | low | PASS |
| `2_allergen_peanut` | 5/5 | high | PASS |
| `3_preservatives_chips` | 4/5 | low | PARTIAL |
| `4_goal_conflict_low_sodium` | 4/4 | high | PASS |
| `5_multi_issue_cereal` | 7/7 | moderate | PASS |

## Per-case detail

### `1_clean_pass_oats`

_Plain rolled oats, general health profile — baseline. LLM should return low risk, empty allergen/preservative lists, and a positive goal alignment._

- **Overall risk:** `low`
- **Summary:** This whole grain oat product is a healthy choice, providing a good amount of dietary fiber and some essential minerals with no major nutrient concerns.

- **allergen_flags:** (none)
- **preservative_flags:** (none)
- **nutrient_flags:**
  - dietary fiber: 14% DV per serving (notably high)
  - total carbs: 10% DV per serving (moderate)
- **goal_alignment:**
  - general health goal: SUPPORT — provides whole grain, fiber, and some essential minerals
- **recommendations:**
  - Pair with a source of protein and healthy fat for a balanced meal
  - Consider as a healthy snack option

**Checks:**

- ✓ **[risk]** overall_risk='low' ∈ ['low']
- ✓ **[min_recs]** len(recommendations)=2 >= 1
- ✓ **[forbidden_allergen]** forbidden 'wheat' in allergen_flags — absent
- ✓ **[forbidden_allergen]** forbidden 'soy' in allergen_flags — absent
- ✓ **[forbidden_allergen]** forbidden 'dairy' in allergen_flags — absent
- ✓ **[forbidden_allergen]** forbidden 'egg' in allergen_flags — absent
- ✓ **[forbidden_preservative]** forbidden 'BHT' in preservative_flags — absent
- ✓ **[forbidden_preservative]** forbidden 'BHA' in preservative_flags — absent
- ✓ **[forbidden_preservative]** forbidden 'TBHQ' in preservative_flags — absent

### `2_allergen_peanut`

_Peanut butter cup for a peanut-allergic user. Must flag peanut specifically and return high overall risk._

- **Overall risk:** `high`
- **Summary:** This product may pose a risk due to the presence of peanuts and high amounts of added sugars and saturated fat.

- **allergen_flags:**
  - peanut: listed in ingredients
- **preservative_flags:**
  - TBHQ: synthetic preservative
- **nutrient_flags:**
  - added sugars: 40% DV per serving (high)
  - saturated fat: 25% DV per serving (high)
- **goal_alignment:**
  - general health goal: CONFLICT — high added sugars and saturated fat content
- **recommendations:**
  - Choose a product with less added sugars
  - Limit to half a serving to reduce saturated fat intake

**Checks:**

- ✓ **[allergen]** expected 'peanut' in allergen_flags — FOUND
- ✓ **[preservative]** expected 'TBHQ' in preservative_flags — FOUND
- ✓ **[nutrient]** expected 'sugar' in nutrient_flags — FOUND
- ✓ **[risk]** overall_risk='high' ∈ ['high']
- ✓ **[min_recs]** len(recommendations)=2 >= 1

### `3_preservatives_chips`

_Fried snack with BHT + BHA + TBHQ. No user allergens. Must flag preservatives and surface sodium/saturated fat._

- **Overall risk:** `low`
- **Summary:** This product is a relatively balanced snack, but low in essential nutrients like fiber and protein, and contains synthetic preservatives.

- **allergen_flags:** (none)
- **preservative_flags:**
  - BHT: synthetic antioxidant
  - BHA: synthetic antioxidant
  - TBHQ: synthetic antioxidant
- **nutrient_flags:**
  - dietary fiber: 4% DV per serving (low)
  - protein: 4% DV per serving (low)
- **goal_alignment:**
  - general health goal: SUPPORT — balanced macronutrient profile, but low in essential nutrients like fiber and protein
- **recommendations:**
  - Pair with a high-fiber side
  - Consider adding a protein source to the meal

**Checks:**

- ✓ **[preservative]** expected 'BHT' in preservative_flags — FOUND
- ✓ **[preservative]** expected 'BHA' in preservative_flags — FOUND
- ✓ **[preservative]** expected 'TBHQ' in preservative_flags — FOUND
- ✗ **[risk]** overall_risk='low' ∉ ['high', 'moderate']
- ✓ **[min_recs]** len(recommendations)=2 >= 1

### `4_goal_conflict_low_sodium`

_Instant ramen for a user with a low-sodium dietary goal. Must flag sodium as a nutrient concern AND as a goal CONFLICT._

- **Overall risk:** `high`
- **Summary:** This product is very high in sodium and saturated fat, and low in dietary fiber, making it a poor choice for a low-sodium diet.

- **allergen_flags:** (none)
- **preservative_flags:**
  - monosodium glutamate: synthetic flavor enhancer
  - caramel color: artificial coloring
- **nutrient_flags:**
  - sodium: 79% DV per serving (very high)
  - saturated fat: 35% DV per serving (high)
  - dietary fiber: 7% DV per serving (low)
- **goal_alignment:**
  - low sodium goal: CONFLICT — 79% DV sodium
- **recommendations:**
  - Limit to half a serving
  - Pair with a low-sodium side
  - Choose a lower-sodium alternative

**Checks:**

- ✓ **[nutrient]** expected 'sodium' in nutrient_flags — FOUND
- ✓ **[goal]** expected CONFLICT entry mentioning 'sodium' — FOUND
- ✓ **[risk]** overall_risk='high' ∈ ['high']
- ✓ **[min_recs]** len(recommendations)=3 >= 1

### `5_multi_issue_cereal`

_Sugary chocolate-milk kids cereal for a lactose-intolerant user with a low-added-sugar goal. Expect cascading flags across allergen, preservative, nutrient, and goal-alignment dimensions._

- **Overall risk:** `moderate`
- **Summary:** This product is high in added sugars and may not be suitable for lactose intolerant individuals due to the presence of nonfat milk.

- **allergen_flags:**
  - nonfat milk: listed in ingredients, potential issue for lactose intolerance
- **preservative_flags:**
  - BHT: synthetic antioxidant
  - Red 40: artificial coloring
  - Yellow 5: artificial coloring
- **nutrient_flags:**
  - added sugars: 34% DV per serving (high)
- **goal_alignment:**
  - low added sugar goal: CONFLICT — 34% DV added sugars
- **recommendations:**
  - Limit to half a serving
  - Pair with a low-sugar side
  - Consider lactose-free alternative

**Checks:**

- ✓ **[allergen]** expected 'milk' in allergen_flags — FOUND
- ✓ **[preservative]** expected 'BHT' in preservative_flags — FOUND
- ✓ **[nutrient]** expected 'added sugar' in nutrient_flags — FOUND
- ✓ **[nutrient]** expected 'sugar' in nutrient_flags — FOUND
- ✓ **[goal]** expected CONFLICT entry mentioning 'sugar' — FOUND
- ✓ **[risk]** overall_risk='moderate' ∈ ['high', 'moderate']
- ✓ **[min_recs]** len(recommendations)=3 >= 2

