import json
import math
import re
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "nutrition_reference.json"
NUTRIENT_FIELDS = (
    "calories_kcal",
    "protein_g",
    "carbs_g",
    "fats_g",
    "fiber_g",
    "sugar_g",
)
REQUIRED_FIELDS = {"aliases", "default_serving_g", *NUTRIENT_FIELDS}


class NutritionReferenceError(ValueError):
    pass


def _normalize_alias(alias: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", alias.casefold()).strip()


def _validate_entry(
    food_name: str,
    entry: Any,
    aliases_by_name: dict[str, str],
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise NutritionReferenceError(
            f"Nutrition reference entry {food_name!r} must be a JSON object."
        )

    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        raise NutritionReferenceError(
            f"Nutrition reference entry {food_name!r} is missing required "
            f"field(s): {', '.join(sorted(missing))}."
        )

    aliases = entry["aliases"]
    if not isinstance(aliases, list) or not aliases:
        raise NutritionReferenceError(
            f"Nutrition reference entry {food_name!r} must have a non-empty aliases list."
        )

    normalized_food_name = _normalize_alias(food_name)
    existing_food = aliases_by_name.get(normalized_food_name)
    if existing_food is not None:
        raise NutritionReferenceError(
            f"Duplicate nutrition alias {food_name!r} in entries "
            f"{existing_food!r} and {food_name!r}."
        )
    aliases_by_name[normalized_food_name] = food_name

    validated_aliases = []
    aliases_in_entry = set()
    for alias in aliases:
        if not isinstance(alias, str) or not alias.strip():
            raise NutritionReferenceError(
                f"Nutrition reference entry {food_name!r} has an invalid alias."
            )
        cleaned_alias = alias.strip()
        normalized = _normalize_alias(cleaned_alias)
        if not normalized:
            raise NutritionReferenceError(
                f"Nutrition reference entry {food_name!r} has an invalid alias."
            )
        if normalized in aliases_in_entry:
            raise NutritionReferenceError(
                f"Nutrition reference entry {food_name!r} has duplicate alias "
                f"{cleaned_alias!r}."
            )
        aliases_in_entry.add(normalized)
        existing_food = aliases_by_name.get(normalized)
        if existing_food is not None and existing_food != food_name:
            raise NutritionReferenceError(
                f"Duplicate nutrition alias {cleaned_alias!r} in entries "
                f"{existing_food!r} and {food_name!r}."
            )
        aliases_by_name.setdefault(normalized, food_name)
        validated_aliases.append(cleaned_alias)

    serving_size = entry["default_serving_g"]
    if (
        isinstance(serving_size, bool)
        or not isinstance(serving_size, (int, float))
        or not math.isfinite(serving_size)
        or serving_size <= 0
    ):
        raise NutritionReferenceError(
            f"Nutrition reference entry {food_name!r} has invalid "
            "default_serving_g; expected a positive finite number."
        )

    for field in NUTRIENT_FIELDS:
        value = entry[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise NutritionReferenceError(
                f"Nutrition reference entry {food_name!r} has invalid {field}; "
                "expected a non-negative finite number per 100 g."
            )

    source = entry.get("source")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise NutritionReferenceError(
            f"Nutrition reference entry {food_name!r} has invalid source; "
            "expected a non-empty string."
        )

    validated = dict(entry)
    validated["aliases"] = tuple(validated_aliases)
    return validated


def load_nutrition_reference(path: Path = DATA_FILE) -> dict[str, dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as reference_file:
            raw_reference = json.load(reference_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise NutritionReferenceError(
            f"Could not load nutrition reference file {path}: {exc}"
        ) from exc

    if not isinstance(raw_reference, dict) or not raw_reference:
        raise NutritionReferenceError(
            f"Nutrition reference file {path} must contain a non-empty JSON object."
        )

    aliases_by_name: dict[str, str] = {}
    validated_reference = {}
    for food_name, entry in raw_reference.items():
        if not isinstance(food_name, str) or not food_name.strip():
            raise NutritionReferenceError(
                f"Nutrition reference file {path} contains an invalid food name."
            )
        validated_reference[food_name] = _validate_entry(
            food_name,
            entry,
            aliases_by_name,
        )
    return validated_reference


LOCAL_NUTRITION_REFERENCE = load_nutrition_reference()
