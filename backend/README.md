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
