import json
import logging

import pytest

from backend.services import nutrition_estimation
from backend.services.nutrition_reference import (
    LOCAL_NUTRITION_REFERENCE,
    NutritionReferenceError,
    load_nutrition_reference,
)


def valid_entry(**overrides):
    entry = {
        "aliases": ["sample food", "sample"],
        "default_serving_g": 100,
        "calories_kcal": 150,
        "protein_g": 5,
        "carbs_g": 20,
        "fats_g": 4,
        "fiber_g": 3,
        "sugar_g": 2,
    }
    entry.update(overrides)
    return entry


def write_reference(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_json_once_into_compatible_reference_structure():
    assert isinstance(LOCAL_NUTRITION_REFERENCE["cooked white rice"]["aliases"], tuple)
    assert LOCAL_NUTRITION_REFERENCE["cooked white rice"]["default_serving_g"] == 158
    assert LOCAL_NUTRITION_REFERENCE["samosa"]["calories_kcal"] == 310
    assert "USDA FDC 2708730" in LOCAL_NUTRITION_REFERENCE["samosa"]["source"]
    assert "source" not in LOCAL_NUTRITION_REFERENCE["paneer"]


def test_loader_reports_missing_required_field(tmp_path):
    missing = valid_entry()
    del missing["fiber_g"]
    path = write_reference(tmp_path / "reference.json", {"sample": missing})

    with pytest.raises(NutritionReferenceError, match="fiber_g"):
        load_nutrition_reference(path)


def test_loader_rejects_duplicate_aliases_across_entries(tmp_path):
    path = write_reference(
        tmp_path / "reference.json",
        {
            "first food": valid_entry(aliases=["first food", "shared alias"]),
            "second food": valid_entry(aliases=["second food", "shared alias"]),
        },
    )

    with pytest.raises(NutritionReferenceError, match="Duplicate nutrition alias"):
        load_nutrition_reference(path)


def test_loader_rejects_non_numeric_nutrient(tmp_path):
    path = write_reference(
        tmp_path / "reference.json",
        {"sample": valid_entry(protein_g="a lot")},
    )

    with pytest.raises(NutritionReferenceError, match="protein_g"):
        load_nutrition_reference(path)


def test_new_food_aliases_match_canonical_entries():
    samosa_match = nutrition_estimation._find_local_food("samosas")
    radish_match = nutrition_estimation._find_local_food("mooli")

    assert samosa_match is not None and samosa_match[0] == "samosa"
    assert radish_match is not None and radish_match[0] == "radish"


def test_unmatched_dish_and_item_are_logged_by_name_only(monkeypatch, caplog):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    with caplog.at_level(logging.INFO, logger=nutrition_estimation.__name__):
        nutrition_estimation.asyncio.run(
            nutrition_estimation.estimate_nutrition(
                "unmatched dish",
                ["unmatched ingredient"],
            )
        )

    assert "No nutrition reference match for food: unmatched dish" in caplog.text
    assert "No nutrition reference match for food: unmatched ingredient" in caplog.text
