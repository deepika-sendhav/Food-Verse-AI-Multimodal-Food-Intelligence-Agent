# Food image recognition

The endpoint accepts a JPG, PNG, or WEBP file as multipart form data:

- **Method:** `POST`
- **Path:** `/api/food-recognition/analyze`
- **Upload field:** `file`
- **Optional serving weight:** `serving_size_g` (numeric grams; maximum 5,000)
- **Swagger UI:** open `/docs`, expand `POST /api/food-recognition/analyze`, choose an image, and select **Execute**.

Successful responses contain `success`, `dish_name` (or `null` when unclear),
`detected_items`, `confidence` (`null` because the vision chat model does not
provide a calibrated classification probability), `description`, and
`uncertainties`. Nutrition results are grouped in `nutrition`; `health_score`,
`health_label`, `reasoning`, `insights`, and `alternatives` are also returned.
Nutrition values are estimates for the declared serving, not medical advice.

Nutrition lookup prefers USDA FoodData Central when `USDA_FDC_API_KEY` is set.
If that service cannot provide a usable match, the estimator uses the small
local reference table in `backend/data/nutrition_reference.json`, loaded and
validated once when the nutrition-reference module is imported. Aliases are
exposed as tuples to the estimator. Existing reference values are rounded
estimates per 100 g; the sourced additions include their USDA FDC record in
`source`. Foods without verified values are listed in
`backend/data/needs_review.md` and are not guessed. For unmatched foods,
numeric values and a score are withheld rather than guessed. A caller can send
`serving_size_g` as another multipart form field to replace the assumed serving
weight.

The health score is a transparent project heuristic, not a clinical rating:
start at 50; add up to 20 points for protein (1 point per gram), add up to 20
for fiber (2.5 points per gram), subtract 5 points at 10 g total sugar or 10 at
20 g, subtract 10 points above 700 kcal or 20 above 1,000 kcal, then clamp to
0-100. Labels are Excellent (80+), Good (65-79), Moderate (45-64), and Limit
(below 45). The estimator lists the score factors in `reasoning`.

Configure the variables shown in the repository's `.env.example`. `GROQ_API_KEY`
is required for image analysis; `USDA_FDC_API_KEY` is optional. Run commands
from the repository root:

```powershell
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
python -m pytest backend/tests -q
```

Example response shape:

```json
{
  "success": true,
  "dish_name": "banana",
  "detected_items": ["banana"],
  "confidence": null,
  "description": "A banana.",
  "uncertainties": ["Serving size of 118 g is an assumption, not measured from the image."],
  "nutrition": {
    "serving_size_g": 118,
    "serving_description": "118 g of banana (reference serving assumption)",
    "calories_kcal": 105,
    "protein_g": 1.3,
    "carbs_g": 27,
    "fats_g": 0.4,
    "fiber_g": 3.1,
    "sugar_g": 14.4,
    "source": "Local nutrition reference (approximate values per 100 g)",
    "serving_size_is_assumed": true,
    "uncertainties": ["..."]
  },
  "health_score": 54,
  "health_label": "Moderate",
  "reasoning": "Base score: 50. ...",
  "insights": ["..."],
  "alternatives": ["..."]
}
```

## Freshness image features

`POST /api/freshness/features` accepts an image in the multipart `file` field.
It reuses the safe Pillow image decoder, EXIF correction, maximum pixel limit,
and resize path. It then applies OpenCV colored noise reduction and CLAHE
lighting normalization to the LAB lightness channel. This endpoint only
measures image features; it does not classify freshness or call an LLM.

The `FreshnessFeatures` response has `feature_version`, `color`,
`dark_discoloration_fraction`, `yellow_brown_fraction`, `texture`,
`surface_patterns`, `quality_flags`, and `warnings`.

| Feature | Range | Computation |
| --- | --- | --- |
| `color.mean_h`, `color.std_h` | H: 0–179; std: 0–90 | Mean and population standard deviation of OpenCV HSV hue. |
| `color.mean_s`, `color.mean_v` | 0–255 | Mean HSV saturation and value. |
| `color.std_s`, `color.std_v` | 0–127.5 | Population standard deviation of HSV saturation and value. |
| `color.dominant_colors` | RGB channels: 0–255; percentage: 0–100 | Three k-means clusters in RGB with each cluster's pixel share. Percentages sum to approximately 100. |
| `color.consistency_score` | 0–1 | One minus the mean normalized hue and saturation spread; higher means more consistent color. |
| `dark_discoloration_fraction` | 0–1 | Fraction of normalized HSV pixels in dark range H 0–179, S 0–255, V 0–55. |
| `yellow_brown_fraction` | 0–1 | Fraction of normalized HSV pixels in either brown range H 5–25, S 45–255, V 20–190 or yellow range H 20–40, S 45–255, V 80–255. |
| `texture.laplacian_variance` | 0–1,000,000,000 | Variance of the grayscale Laplacian; higher often means more high-frequency detail. |
| `texture.local_standard_deviation` | 0–127.5 | Mean grayscale standard deviation in 7×7 neighborhoods. |
| `texture.smoothness_score` | 0–1 | One minus local standard deviation divided by 127.5; higher indicates locally smoother pixels. |
| `surface_patterns.edge_density` | 0–1 | Fraction of Canny edge pixels, with thresholds 100 and 200. |
| `surface_patterns.mold_like_pattern_fraction` | 0–1 | Fraction of image area from small irregular contours within white/gray (S 0–70, V 80–255) or green-blue (H 35–100, S 20–255, V 25–200) HSV candidate masks. |
| `quality_flags.too_dark` | Boolean | True if mean normalized HSV value is below 50. |
| `quality_flags.too_bright` | Boolean | True if mean normalized HSV value is above 220. |
| `quality_flags.blurry` | Boolean | True if grayscale Laplacian variance is below 20. |
| `quality_flags.low_contrast` | Boolean | True if grayscale standard deviation is below 15. |

`validate_features()` checks finite numeric values, documented ranges, and
dominant-color percentages. These features are visual heuristics, not proof of
spoilage or food safety. Lighting, camera characteristics, and natural food
color (for example, ripe bananas or dark foods) affect them.

## Freshness classification and safety recommendations

`POST /api/freshness/analyze` accepts a JPG, PNG, or WEBP image in the multipart
`file` field, plus optional `storage_time` and `storage_type` form fields. It
uses the same upload validation and size limit as `/api/freshness/features`.
The API first extracts the existing image features, computes a rule-based
score, then asks the configured Groq vision model for a separate visual
assessment using the image, measured features, and any supplied storage
context. Code combines these results; the model does not choose the final
verdict or return confidence. If the vision service times out, is unavailable,
or returns invalid JSON, the endpoint still returns a rules-only estimate and
records the skipped model assessment in `uncertainties`.

The feature-based score starts at 100 and applies documented penalties for
yellow/brown and dark discoloration, mold-like surface patterns, low smoothness,
low color consistency, and image-quality flags. Scores map to levels as
follows: 70–100 is `fresh`, 40–69 is `moderately_fresh`, and below 40 is
`spoiled`. A model and rule agreement supports a stronger confidence estimate;
a one-level disagreement lowers confidence and chooses the more cautious
(less-fresh) level. A two-level disagreement, or an uncertain model assessment,
produces `uncertain`, except a mold-like fraction of at least 1% leads to the
more cautious `spoiled` result. Poor lighting, blur, and low contrast lower
confidence. Confidence is computed by the backend and capped at 90.

| Final level | Safety status | Recommendation |
| --- | --- | --- |
| `fresh` | Likely safe | Store properly and consume within the usual time. |
| `moderately_fresh` | Consume soon | Use today or cook thoroughly; check smell and texture. |
| `spoiled` | Unsafe | Discard it; do not taste it to test. |
| `uncertain` | Cannot determine | Retake a clearer photo and check smell, texture, and date. |

Reported room-temperature storage exceeding two hours and recognized rice,
meat, fish, or dairy item names can add extra safety warnings. The fixed
disclaimer is: “This is a visual estimate, not a food safety guarantee. When
in doubt, throw it out.” Freshness classification is a visual estimate, not a
food safety test; one image cannot establish smell, internal condition,
temperature history, or pathogen presence. Follow food-safety guidance and
discard food when there is doubt.

## Kitchen hygiene screening from video

`POST /api/hygiene/analyze` accepts an MP4, MOV, AVI, or WEBM video, or a JPG,
PNG, or WEBP still image. Upload the media in multipart field `file`; optional
fields are `interval_seconds` (1–30, default 5) and `context_rules` (up to 500
characters). The video defaults are 50 MB, 120 seconds, and at most 12 sampled
frames. Configure these with `HYGIENE_VIDEO_MAX_BYTES`,
`HYGIENE_VIDEO_MAX_SECONDS`, and `HYGIENE_MAX_FRAMES`. Vision processing is
sequential by default (`HYGIENE_MAX_CONCURRENCY=1`) with a two-second delay
between frames (`HYGIENE_FRAME_DELAY_SECONDS=2`). Frames are capped to a
768-pixel longest side before submission (`HYGIENE_FRAME_MAX_SIDE=768`).
Rate-limited requests honor `Retry-After` up to 20 seconds, or use 2/4/8-second
exponential delays, with at most three retries per frame.

The pipeline validates and temporarily writes video uploads, samples frames at
the requested interval, preprocesses sampled frames using the shared image
preprocessor, then skips frames that are blurry, too dark, low contrast, or
near-duplicates. The temporary video is deleted after frame extraction; image
and frame bytes remain in memory only for the request and are not returned or
logged. Each selected frame is analyzed independently with the vision model,
with concurrency controlled by `HYGIENE_MAX_CONCURRENCY`. A failed frame is listed in
`frames_failed`; if all selected frame calls fail, the endpoint returns 503.
If some succeed, the response contains a partial analysis.

The model supplies only observations—`compliant`, `violation`, `not_visible`,
or `unclear`—and a short visible-evidence string for:

- Protective equipment: gloves in use, hair covering, and apron or clean
  uniform.
- Food handling: hand-to-face/hair contact, personal phone use, bare-hand food
  contact, food on the floor or unsafe storage, and raw/cooked cross-contact
  risk.
- Cleanliness: work-surface cleanliness and floor cleanliness.

Only observable compliant/violation results enter scoring; `not_visible` and
`unclear` are excluded from both the score denominator and numerator. The
fixed indicator weights (total 100) are gloves 12, hair covering 10, apron or
uniform 8, hand/face contact 10, phone use 10, bare-hand contact 16, unsafe
floor/storage 12, surface cleanliness 4, floor cleanliness 2, and
raw/cooked cross-contact 16. Category scores use the same weights within their
category. Evidence coverage is the share of indicator observations that are
observable across analyzed frames. Below 50% coverage, `overall_score` is
`null` and status is `insufficient_evidence`; category scores are also `null`
in that case. Each category has its own `category_evidence_coverage` ratio.
Categories with less than 50% coverage have a `null` score, even if the
overall report has sufficient evidence.

An observed violation is `confirmed` only if it appears in at least two
analyzed frames; a one-frame signal is always `possible`, including High
severity and single-image reports. Severity is fixed in code: High for hand-to-face/hair
contact, unsafe floor/storage, and raw/cooked cross-contact; Medium for bare-hand
food contact, gloves, hair covering, phone use, and surface cleanliness; Low
for apron/uniform and floor cleanliness. Gloves and bare-hand contact are
counted once as a combined concern using the higher weight. A compliant/
violation disagreement across frames is always `possible` and includes a
conflict note. Critical alerts are reserved for confirmed High-severity
signals; a possible High-severity signal raises a warning alert. More than
one-third failed frame analyses adds a partial-footage warning and summary
note. Score bands are 85–100 `good`,
60–84 `needs_attention`, and below 60 `action_required`; low evidence takes
precedence over a numeric band. Suggested actions are phrased as supportive
coaching rather than blame.

This is automated visual screening, not continuous monitoring or a definitive
compliance finding. A single camera angle, occlusion, lighting, and image
quality can cause false positives or false negatives. A human must review
evidence before action. Do not use the report alone for discipline or as a
legal or regulatory compliance determination. `context_rules` is untrusted
supplemental checklist text; it cannot override the required output format or
privacy rules. No identity recognition is performed.

## Smart Kitchen Assistant recipes

`POST /api/kitchen/generate-recipe` accepts multipart form data:

- `text_input` (optional, up to 1,000 characters)
- `file` (optional JPG, PNG, or WEBP image, using the food-image upload size
  limit)
- `servings` (optional integer from 1 to 12; defaults to 2)
- `skill_level` (`beginner`, `intermediate`, or `advanced`; defaults to
  `beginner`)
- `dietary_preferences` (optional, up to 200 characters)

Provide either text, an image, or both. With both, the image is the primary
source and text is additional context. Image bytes are validated and
preprocessed in memory; uploads are not written to disk. A request that is not
food-related or is too unclear returns `status: "needs_clarification"` and a
`clarifying_question` rather than an invented recipe.

Successful recipe responses include `input_type`, `interpreted_goal`, recipe
name and description, ingredients (including quantity, unit, notes, and
`from_input`), ordered steps, time estimates, difficulty, equipment, detected
allergens, safety notes, dietary warnings, substitutions, uncertainties, and a
fixed disclaimer. `total_time_minutes` is calculated from prep and cooking
times when both are provided. Ingredient quantities are approximate; generated
ingredients not visible in an image or mentioned in text are marked
`from_input: false`.

The backend adds conservative safe-handling notes when ingredient names indicate
poultry, pork, minced meat, eggs, fish, or shellfish. It scans ingredient names
for common milk, egg, peanut, tree nut, wheat/gluten, soy, fish, shellfish, and
sesame allergens and reports matches under `allergens.contains`. This scan is
not exhaustive and does not guarantee that an ingredient or product is free
from an allergen. Dietary conflicts such as vegetarian preferences with
chicken are flagged on the ingredient and in `warnings`.

Recipes are AI-generated and are not independently verified. This feature is
not medical advice and provides no medical or allergy guarantee. Check product
labels, all ingredients, allergies, and safe cooking temperatures yourself.
