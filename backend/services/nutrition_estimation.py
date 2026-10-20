import asyncio
import logging
import re
from typing import Any

import httpx

from backend.config import USDA_FDC_API_KEY
from backend.schemas import NutritionInfo
from backend.services.nutrition_reference import LOCAL_NUTRITION_REFERENCE

logger = logging.getLogger(__name__)

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
FDC_TIMEOUT_SECONDS = 5.0
DEFAULT_DISH_SERVING_G = 300.0
GARNISH_ITEMS = {
    "cilantro",
    "coriander",
    "green chili",
    "chili",
    "lime",
    "lemon",
    "mint",
    "curry leaves",
    "parsley",
}
ALLOWED_USDA_DATA_TYPES = {"Foundation", "SR Legacy", "Survey (FNDDS)"}
USDA_PREPARATION_TERMS = {"soup", "canned", "frozen", "mix", "instant"}
MEANINGLESS_MATCH_WORDS = {
    "a",
    "and",
    "dish",
    "food",
    "of",
    "the",
    "with",
}
NUTRIENT_FIELDS = (
    "calories_kcal",
    "protein_g",
    "carbs_g",
    "fats_g",
    "fiber_g",
    "sugar_g",
)
FDC_NUTRIENT_IDS = {
    1008: "calories_kcal",
    2047: "calories_kcal",
    2048: "calories_kcal",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fats_g",
    1079: "fiber_g",
    2000: "sugar_g",
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()


def _find_local_food(name: str) -> tuple[str, dict[str, Any]] | None:
    normalized_name = _normalize_name(name)
    for canonical_name, entry in LOCAL_NUTRITION_REFERENCE.items():
        aliases = (canonical_name, *entry["aliases"])
        if any(_normalize_name(alias) == normalized_name for alias in aliases):
            return canonical_name, entry
    return None


def _per_serving(
    entry: dict[str, Any],
    serving_size_g: float,
) -> dict[str, float | None]:
    factor = serving_size_g / 100
    return {
        field: (
            round(float(entry[field]) * factor, 1)
            if entry.get(field) is not None
            else None
        )
        for field in NUTRIENT_FIELDS
    }


def _score_nutrition(nutrients: dict[str, float]) -> tuple[int, str, str, list[str], list[str]]:
    score = 50
    reasons = ["Base score: 50."]
    insights = []
    alternatives = []

    protein = nutrients["protein_g"]
    protein_points = min(20, round(protein))
    score += protein_points
    reasons.append(f"Protein adds {protein_points} points (up to 20 points).")
    if protein < 10:
        insights.append("This serving provides less than 10 g of protein.")

    fiber = nutrients["fiber_g"]
    fiber_points = min(20, round(fiber * 2.5))
    score += fiber_points
    reasons.append(f"Fiber adds {fiber_points} points (up to 20 points at 8 g).")
    if fiber < 4:
        insights.append("This serving is relatively low in fiber.")
        alternatives.append("Add beans, lentils, vegetables, or a whole-grain side for more fiber.")

    sugar = nutrients["sugar_g"]
    if sugar >= 20:
        score -= 10
        reasons.append("Total sugar estimate of 20 g or more subtracts 10 points.")
        insights.append("This serving has an estimated 20 g or more of sugar.")
        alternatives.append("Choose an unsweetened version or reduce added sweeteners.")
    elif sugar >= 10:
        score -= 5
        reasons.append("Total sugar estimate of 10-19.9 g subtracts 5 points.")

    calories = nutrients["calories_kcal"]
    if calories > 1000:
        score -= 20
        reasons.append("More than 1,000 kcal per serving subtracts 20 points.")
        alternatives.append("Consider a smaller portion or split the serving.")
    elif calories > 700:
        score -= 10
        reasons.append("More than 700 kcal per serving subtracts 10 points.")
        alternatives.append("Consider a smaller portion or pair it with vegetables.")

    score = max(0, min(100, score))
    if score >= 80:
        label = "Excellent"
    elif score >= 65:
        label = "Good"
    elif score >= 45:
        label = "Moderate"
    else:
        label = "Limit"

    if not insights:
        insights.append("The estimated serving has no high-sugar or low-fiber flag under this simple scoring rule.")
    if not alternatives:
        alternatives.append("Pair with vegetables or a whole-grain food for a more balanced meal.")
    return score, label, " ".join(reasons), insights, alternatives


def _nutrition_response(
    *,
    entry: dict[str, Any],
    source: str,
    serving_size_g: float,
    serving_description: str,
    assumed: bool,
    uncertainty: list[str],
) -> tuple[NutritionInfo, int | None, str | None, str, list[str], list[str]]:
    nutrients = _per_serving(entry, serving_size_g)
    if assumed:
        uncertainty.append(
            f"Serving size of {serving_size_g:g} g is an assumption, not measured from the image."
        )
    uncertainty.append(
        "Recipe, brand, cooking method, and added oil or salt can materially change these estimates."
    )
    if any(nutrients[field] is None for field in NUTRIENT_FIELDS):
        score = None
        label = None
        reasoning = "No health score was calculated because the reference is missing one or more nutrients used by the scoring rules."
        insights = ["Some nutrition values were not available from the selected reference."]
        alternatives = []
    else:
        complete_nutrients = {field: float(nutrients[field]) for field in NUTRIENT_FIELDS}
        score, label, reasoning, insights, alternatives = _score_nutrition(
            complete_nutrients
        )
    nutrition = NutritionInfo(
        serving_size_g=serving_size_g,
        serving_description=serving_description,
        **nutrients,
        source=source,
        serving_size_is_assumed=assumed,
        uncertainties=uncertainty,
    )
    return nutrition, score, label, reasoning, insights, alternatives


def _unavailable_multi_item_result(
    *,
    serving_size_g: float | None,
    matched_items: list[str],
    ignored_items: list[str],
    reason: str,
) -> tuple[NutritionInfo, None, None, str, list[str], list[str]]:
    uncertainty = [
        f"Matched detected food items: {', '.join(matched_items) or 'none'}.",
        f"Ignored detected food items: {', '.join(ignored_items) or 'none'}.",
        "Each item portion and the overall serving size are assumptions, not measured from the image.",
        reason,
    ]
    return (
        NutritionInfo(
            serving_size_g=serving_size_g,
            serving_description=(
                f"{serving_size_g:g} g requested; nutrient values unavailable."
                if serving_size_g is not None
                else "Nutrition unavailable for this combination of detected foods."
            ),
            source="Insufficient nutrition reference coverage",
            serving_size_is_assumed=True,
            uncertainties=uncertainty,
        ),
        None,
        None,
        reason,
        ["There were not enough reliable food matches to estimate this dish."],
        [],
    )


async def _estimate_from_detected_items(
    detected_items: list[str],
    serving_size_g: float | None,
) -> tuple[NutritionInfo, int | None, str | None, str, list[str], list[str]]:
    async def find_item_reference(
        item_name: str,
    ) -> tuple[str, dict[str, Any], float, str] | None:
        local_result = _find_local_food(item_name)
        if "stuffed" in item_name.casefold():
            if local_result is None:
                return None
            reference_name, entry = local_result
            return (
                "local",
                entry,
                float(entry["default_serving_g"]),
                reference_name,
            )

        usda_result = await _fetch_usda_food(item_name)
        if usda_result is not None:
            reference_name, per_100_g = usda_result
            return "usda", per_100_g, 100.0, reference_name

        if local_result is None:
            return None
        reference_name, entry = local_result
        return (
            "local",
            entry,
            float(entry["default_serving_g"]),
            reference_name,
        )

    item_references = await asyncio.gather(
        *(find_item_reference(item) for item in detected_items)
    )

    matched: list[tuple[str, dict[str, Any], float, str]] = []
    ignored_items = []
    item_portions: dict[str, float] = {}
    for item_name, reference in zip(detected_items, item_references):
        if reference is None:
            ignored_items.append(item_name)
            item_portions[item_name] = 100.0
            logger.info("No nutrition reference match for food: %s", item_name)
            continue
        _, entry, portion_g, reference_name = reference
        matched.append((item_name, entry, portion_g, reference_name))
        item_portions[item_name] = portion_g

    matched_items = [item_name for item_name, *_ in matched]
    non_garnish_items = [
        item for item in detected_items if _normalize_name(item) not in GARNISH_ITEMS
    ]
    total_non_garnish_portions_g = sum(item_portions[item] for item in non_garnish_items)
    matched_non_garnish_portions_g = sum(
        item_portions[item]
        for item in non_garnish_items
        if item in matched_items
    )
    coverage = (
        matched_non_garnish_portions_g / total_non_garnish_portions_g
        if total_non_garnish_portions_g
        else 0.0
    )
    if coverage < 0.6:
        reason = (
            f"Reliable references cover {matched_non_garnish_portions_g:g} g of "
            f"{total_non_garnish_portions_g:g} g of non-garnish food "
            f"({coverage:.0%}; less than 60%); nutrition "
            "values and the health score are withheld."
        )
        return _unavailable_multi_item_result(
            serving_size_g=serving_size_g,
            matched_items=matched_items,
            ignored_items=ignored_items,
            reason=reason,
        )

    assumed_total_size = sum(portion_g for _, _, portion_g, _ in matched)
    if assumed_total_size <= 0:
        reason = (
            "No non-garnish food items were available to estimate a serving; "
            "nutrition values and the health score are withheld."
        )
        return _unavailable_multi_item_result(
            serving_size_g=serving_size_g,
            matched_items=matched_items,
            ignored_items=ignored_items,
            reason=reason,
        )
    final_serving_size_g = serving_size_g or DEFAULT_DISH_SERVING_G
    scaling_factor = final_serving_size_g / assumed_total_size
    aggregate: dict[str, float | None] = {}
    for field in NUTRIENT_FIELDS:
        if any(entry.get(field) is None for _, entry, _, _ in matched):
            aggregate[field] = None
            continue
        total_at_reference_portions = sum(
            float(entry[field]) * portion_g / 100
            for _, entry, portion_g, _ in matched
        )
        aggregate[field] = round(total_at_reference_portions * scaling_factor, 1)

    uncertainty = [
        f"Matched detected food items: {', '.join(matched_items)}.",
        f"Ignored detected food items: {', '.join(ignored_items) or 'none'}.",
        (
            f"Reference portions were assumed: "
            + "; ".join(
                f"{item_name} {portion_g:g} g ({reference_name})"
                for item_name, _, portion_g, reference_name in matched
            )
            + "."
        ),
        (
            f"The combined reference portions total {assumed_total_size:g} g and "
            f"were scaled to a {final_serving_size_g:g} g serving."
        ),
        "Item quantities are estimated from reference serving sizes, not measured from the image.",
        "Recipe, brand, cooking method, and added oil or salt can materially change these estimates.",
    ]
    if USDA_FDC_API_KEY:
        uncertainty.append(
            "USDA FoodData Central was unavailable or had no usable match for some items; local references were used where available."
        )

    if any(aggregate[field] is None for field in NUTRIENT_FIELDS):
        score = None
        label = None
        reasoning = (
            "No health score was calculated because one or more matched item "
            "references are missing nutrients required by the scoring rules."
        )
        insights = ["Some nutrition values were unavailable in the matched references."]
        alternatives = []
    else:
        complete_aggregate = {
            field: float(aggregate[field]) for field in NUTRIENT_FIELDS
        }
        score, label, reasoning, insights, alternatives = _score_nutrition(
            complete_aggregate
        )

    nutrition = NutritionInfo(
        serving_size_g=final_serving_size_g,
        serving_description=(
            f"{final_serving_size_g:g} g estimated combined serving"
            + (
                " (requested serving weight)"
                if serving_size_g is not None
                else " (default serving assumption)"
            )
        ),
        **aggregate,
        source="Combined USDA FoodData Central and local nutrition references",
        serving_size_is_assumed=True,
        uncertainties=uncertainty,
    )
    return nutrition, score, label, reasoning, insights, alternatives


def _usda_nutrients(food: dict[str, Any]) -> dict[str, float | None] | None:
    nutrients: dict[str, float | None] = {
        field: None for field in NUTRIENT_FIELDS
    }
    for item in food.get("foodNutrients", []):
        nutrient_id = item.get("nutrientId")
        field = FDC_NUTRIENT_IDS.get(nutrient_id)
        amount = item.get("value")
        if field is None or amount is None:
            continue
        try:
            value = float(amount)
        except (TypeError, ValueError):
            continue
        unit = str(item.get("unitName", "")).casefold()
        if field == "calories_kcal":
            if unit == "kj":
                value *= 0.239005736
            elif unit not in {"kcal", "cal"}:
                continue
        elif unit == "mg":
            value /= 1000
        elif unit not in {"g", "gram", "grams"}:
            continue
        nutrients[field] = value
    if nutrients["calories_kcal"] is None:
        return None
    return nutrients


async def _fetch_usda_food(
    query: str,
) -> tuple[str, dict[str, float | None]] | None:
    records = await _fetch_usda_food_records(query)
    for description, nutrients, data_type in records:
        if data_type in ALLOWED_USDA_DATA_TYPES:
            return description, nutrients
    return None


async def _fetch_usda_food_records(
    query: str,
) -> list[tuple[str, dict[str, float | None], str | None]]:
    if not USDA_FDC_API_KEY:
        return []
    params = {
        "api_key": USDA_FDC_API_KEY,
        "query": query,
        "pageSize": 10,
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
    }
    try:
        async with httpx.AsyncClient(timeout=FDC_TIMEOUT_SECONDS) as client:
            response = await client.get(FDC_SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("USDA FoodData Central lookup failed; using local reference data.")
        return []

    if not isinstance(payload, dict):
        logger.warning("USDA FoodData Central returned an unexpected response.")
        return []
    foods = payload.get("foods", [])
    if not isinstance(foods, list):
        logger.warning("USDA FoodData Central returned an unexpected food list.")
        return []
    records = []
    for food in foods:
        if not isinstance(food, dict):
            continue
        nutrients = _usda_nutrients(food)
        if nutrients:
            records.append(
                (
                    food.get("description", query),
                    nutrients,
                    food.get("dataType"),
                )
            )
    return records


def _whole_dish_usda_rejection_reason(
    dish_name: str,
    description: str,
    data_type: str | None,
) -> str | None:
    if data_type not in ALLOWED_USDA_DATA_TYPES:
        return f"unsupported USDA data type {data_type!r}"

    dish_words = set(re.findall(r"[a-z0-9]+", dish_name.casefold()))
    description_words = set(re.findall(r"[a-z0-9]+", description.casefold()))
    meaningful_words = dish_words - MEANINGLESS_MATCH_WORDS
    if not meaningful_words.intersection(description_words):
        return "the description shares no meaningful word with the dish name"

    uppercase_prefix = re.match(r"^([A-Z][A-Z0-9 '&.-]*),", description)
    if uppercase_prefix and any(character.isalpha() for character in uppercase_prefix[1]):
        return "the description starts with an uppercase brand-style prefix"

    for term in USDA_PREPARATION_TERMS:
        if (
            re.search(rf"\b{re.escape(term)}\b", description, re.IGNORECASE)
            and not re.search(rf"\b{re.escape(term)}\b", dish_name, re.IGNORECASE)
        ):
            return f"the description contains {term!r}, which is absent from the dish name"
    return None


def _is_combination_dish(dish_name: str) -> bool:
    return bool(re.search(r"\s+with\s+|\s+and\s+|&|,", dish_name, re.IGNORECASE))


async def estimate_nutrition(
    dish_name: str | None,
    detected_items: list[str],
    serving_size_g: float | None = None,
) -> tuple[NutritionInfo, int | None, str | None, str, list[str], list[str]]:
    if not dish_name:
        return (
            NutritionInfo(
                serving_size_g=serving_size_g,
                serving_description="Not available: the food could not be identified.",
                source="No reliable food match",
                serving_size_is_assumed=serving_size_g is None,
                uncertainties=[
                    "Nutrition cannot be estimated until a food or dish is identified."
                ],
            ),
            None,
            None,
            "No nutrition score was calculated because there is no reliable food match.",
            ["The image model could not identify a dish with enough certainty."],
            [],
        )

    uncertainty = []
    rejected_usda_description = None
    is_combination = _is_combination_dish(dish_name)
    usda_matches = (
        []
        if is_combination
        else await _fetch_usda_food_records(dish_name)
    )
    for usda_name, per_100_g, data_type in usda_matches:
        rejection_reason = _whole_dish_usda_rejection_reason(
            dish_name,
            usda_name,
            data_type,
        )
        if rejection_reason:
            rejected_usda_description = (
                f"Rejected USDA description {usda_name!r}: {rejection_reason}."
            )
            uncertainty.append(rejected_usda_description)
            continue
        size = serving_size_g or DEFAULT_DISH_SERVING_G
        assumed = serving_size_g is None
        serving_description = (
            f"{size:g} g of {usda_name}"
            + (" (standard dish serving assumption)" if assumed else " (user-supplied serving weight)")
        )
        return _nutrition_response(
            entry=per_100_g,
            source="USDA FoodData Central (per 100 g reference estimate)",
            serving_size_g=size,
            serving_description=serving_description,
            assumed=assumed,
            uncertainty=uncertainty,
        )

    if USDA_FDC_API_KEY and not is_combination:
        uncertainty.append(
            "USDA FoodData Central was unavailable or had no usable match; a local reference is used if available."
        )

    local_match = _find_local_food(dish_name)
    matched_name = dish_name
    if local_match is None:
        logger.info("No nutrition reference match for food: %s", dish_name)
        if len(detected_items) == 1:
            local_match = _find_local_food(detected_items[0])
            if local_match:
                matched_name = detected_items[0]

    if local_match is not None:
        canonical_name, entry = local_match
        default_size = float(entry["default_serving_g"])
        size = serving_size_g or default_size
        assumed = serving_size_g is None
        serving_description = (
            f"{size:g} g of {canonical_name}"
            + (" (reference serving assumption)" if assumed else " (user-supplied serving weight)")
        )
        return _nutrition_response(
            entry=entry,
            source="Local nutrition reference (approximate values per 100 g)",
            serving_size_g=size,
            serving_description=serving_description,
            assumed=assumed,
            uncertainty=uncertainty,
        )

    if len(detected_items) > 1:
        multi_item_result = await _estimate_from_detected_items(
            detected_items,
            serving_size_g,
        )
        if rejected_usda_description:
            multi_item_result[0].uncertainties.append(rejected_usda_description)
        return multi_item_result

    for item_name in detected_items:
        logger.info("No nutrition reference match for food: %s", item_name)

    uncertainty.append(
        f"No local reference was found for {matched_name!r}; numeric nutrition values and health score are withheld."
    )
    return (
        NutritionInfo(
            serving_size_g=serving_size_g,
            serving_description=(
                f"{serving_size_g:g} g requested; nutrient values unavailable."
                if serving_size_g is not None
                else "Serving size unavailable because no reliable food reference was found."
            ),
            source="No reliable nutrition reference",
            serving_size_is_assumed=serving_size_g is None,
            uncertainties=uncertainty,
        ),
        None,
        None,
        "No health score was calculated because reliable nutrient values are unavailable.",
        ["Nutrition values for this dish could not be verified."],
        [],
    )
