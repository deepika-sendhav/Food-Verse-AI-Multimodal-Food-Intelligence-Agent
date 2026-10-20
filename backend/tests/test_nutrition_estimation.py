import asyncio
from types import SimpleNamespace

import httpx
import pytest

from backend.services import nutrition_estimation
from backend.services.nutrition_estimation import estimate_nutrition


def usda_food(description, calories, protein=5, carbs=20, fat=2, fiber=3, sugar=4):
    return {
        "description": description,
        "dataType": "SR Legacy",
        "foodNutrients": [
            {"nutrientId": 1008, "unitName": "KCAL", "value": calories},
            {"nutrientId": 1003, "unitName": "G", "value": protein},
            {"nutrientId": 1005, "unitName": "G", "value": carbs},
            {"nutrientId": 1004, "unitName": "G", "value": fat},
            {"nutrientId": 1079, "unitName": "G", "value": fiber},
            {"nutrientId": 2000, "unitName": "G", "value": sugar},
        ],
    }


def test_local_reference_scales_values_to_documented_serving(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, score, label, reasoning, _insights, _alternatives = asyncio.run(
        estimate_nutrition("rice", [])
    )

    assert nutrition.serving_size_g == 158
    assert nutrition.serving_size_is_assumed is True
    assert nutrition.calories_kcal == 205.4
    assert nutrition.protein_g == 4.3
    assert nutrition.source.startswith("Local nutrition reference")
    assert score is not None
    assert label is not None
    assert "Base score: 50" in reasoning
    assert any("assumption" in item for item in nutrition.uncertainties)


def test_user_serving_weight_overrides_default(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, *_ = asyncio.run(
        estimate_nutrition("cooked rice", [], serving_size_g=200)
    )

    assert nutrition.serving_size_g == 200
    assert nutrition.calories_kcal == 260
    assert nutrition.serving_size_is_assumed is False
    assert "user-supplied" in nutrition.serving_description


def test_uses_usda_reference_before_local_fallback(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            assert params["api_key"] == "test-key"
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "foods": [
                        {
                            "description": "Rice, cooked",
                            "dataType": "SR Legacy",
                            "foodNutrients": [
                                {"nutrientId": 1008, "unitName": "KCAL", "value": 130},
                                {"nutrientId": 1003, "unitName": "G", "value": 2.7},
                                {"nutrientId": 1005, "unitName": "G", "value": 28.2},
                                {"nutrientId": 1004, "unitName": "G", "value": 0.3},
                                {"nutrientId": 1079, "unitName": "G", "value": 0.4},
                                {"nutrientId": 2000, "unitName": "G", "value": 0.1},
                            ],
                        }
                    ]
                },
            )

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", FakeAsyncClient)

    nutrition, score, _label, _reasoning, _insights, _alternatives = asyncio.run(
        estimate_nutrition("rice", [], serving_size_g=100)
    )

    assert nutrition.source.startswith("USDA FoodData Central")
    assert nutrition.calories_kcal == 130
    assert nutrition.fiber_g == 0.4
    assert score is not None


def test_combination_dish_skips_whole_dish_usda_lookup(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    async def unexpected_whole_dish_lookup(_query):
        raise AssertionError("Whole-dish USDA lookup should be skipped.")

    async def no_item_usda_match(_query):
        return None

    monkeypatch.setattr(
        nutrition_estimation,
        "_fetch_usda_food_records",
        unexpected_whole_dish_lookup,
    )
    monkeypatch.setattr(
        nutrition_estimation,
        "_fetch_usda_food",
        no_item_usda_match,
    )

    nutrition, score, *_ = asyncio.run(
        estimate_nutrition("rice with banana", ["rice", "banana"])
    )

    assert nutrition.calories_kcal is not None
    assert score is not None


@pytest.mark.parametrize(
    ("dish_name", "description", "expected_reason"),
    [
        (
            "vegetable soup",
            "SMART SOUP, creamy vegetable",
            "uppercase brand-style prefix",
        ),
        (
            "vegetable curry",
            "Vegetable soup",
            "contains 'soup'",
        ),
    ],
)
def test_rejects_brand_style_or_mismatched_preparation_description(
    monkeypatch,
    dish_name,
    description,
    expected_reason,
):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    async def fake_usda_records(_query):
        return [(description, nutrition_estimation._usda_nutrients(usda_food(description, 100)), "SR Legacy")]

    monkeypatch.setattr(
        nutrition_estimation,
        "_fetch_usda_food_records",
        fake_usda_records,
    )

    nutrition, score, *_ = asyncio.run(estimate_nutrition(dish_name, []))

    assert nutrition.calories_kcal is None
    assert score is None
    assert any(
        expected_reason in uncertainty
        for uncertainty in nutrition.uncertainties
    )
    assert any(description in uncertainty for uncertainty in nutrition.uncertainties)


def test_accepts_clean_whole_dish_usda_match(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")
    description = "Rice, fried, meatless"

    async def fake_usda_records(_query):
        return [(description, nutrition_estimation._usda_nutrients(usda_food(description, 180)), "SR Legacy")]

    monkeypatch.setattr(
        nutrition_estimation,
        "_fetch_usda_food_records",
        fake_usda_records,
    )

    nutrition, score, *_ = asyncio.run(
        estimate_nutrition("fried rice", [], serving_size_g=100)
    )

    assert nutrition.calories_kcal == 180
    assert nutrition.source.startswith("USDA FoodData Central")
    assert score is not None
    assert not any("Rejected USDA" in item for item in nutrition.uncertainties)


def test_usda_network_error_falls_back_to_local_reference(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    class FailingAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, *_args, **_kwargs):
            request = httpx.Request("GET", nutrition_estimation.FDC_SEARCH_URL)
            raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", FailingAsyncClient)

    nutrition, score, *_ = asyncio.run(estimate_nutrition("banana", []))

    assert nutrition.source.startswith("Local nutrition reference")
    assert nutrition.calories_kcal == 105
    assert score is not None


def test_unknown_food_does_not_invent_nutrients_or_score(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, score, label, reasoning, _insights, _alternatives = asyncio.run(
        estimate_nutrition("unlisted regional stew", ["stew", "herbs"])
    )

    assert nutrition.calories_kcal is None
    assert nutrition.protein_g is None
    assert score is None
    assert label is None
    assert "withheld" in " ".join(nutrition.uncertainties)
    assert "health score are withheld" in reasoning


def test_incomplete_usda_nutrients_withhold_health_score(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    class PartialAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, *_args, **_kwargs):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "foods": [
                        {
                            "description": "Mystery prepared food",
                            "dataType": "Foundation",
                            "foodNutrients": [
                                {"nutrientId": 1008, "unitName": "KCAL", "value": 100},
                                {"nutrientId": 1003, "unitName": "G", "value": 4},
                            ],
                        }
                    ]
                },
            )

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", PartialAsyncClient)

    nutrition, score, label, *_ = asyncio.run(estimate_nutrition("mystery food", []))

    assert nutrition.calories_kcal == 300
    assert nutrition.carbs_g is None
    assert score is None
    assert label is None


def test_health_score_rules_and_labels_are_explicit():
    score, label, reasoning, insights, alternatives = nutrition_estimation._score_nutrition(
        {
            "calories_kcal": 800,
            "protein_g": 15,
            "carbs_g": 40,
            "fats_g": 20,
            "fiber_g": 6,
            "sugar_g": 22,
        }
    )

    assert score == 60
    assert label == "Moderate"
    assert "subtracts 10 points" in reasoning
    assert any("sugar" in insight for insight in insights)
    assert any("unsweetened" in alternative for alternative in alternatives)


def test_multiple_detected_items_aggregate_usda_matches_and_lookup_concurrently(
    monkeypatch,
):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")
    active_lookups = 0
    max_active_lookups = 0

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            nonlocal active_lookups, max_active_lookups
            query = params["query"]
            active_lookups += 1
            max_active_lookups = max(max_active_lookups, active_lookups)
            await asyncio.sleep(0.02)
            active_lookups -= 1
            match = {
                "rice": usda_food("Rice", 130),
                "banana": usda_food("Banana", 89),
            }.get(query)
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"foods": [match] if match else []},
            )

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", FakeAsyncClient)

    nutrition, score, label, _reasoning, _insights, _alternatives = asyncio.run(
        estimate_nutrition("fruit bowl with rice", ["rice", "banana"])
    )

    assert max_active_lookups >= 2
    assert nutrition.serving_size_g == 300
    assert nutrition.calories_kcal == 328.5
    assert nutrition.serving_size_is_assumed is True
    assert score is not None
    assert label is not None
    assert any("rice, banana" in item for item in nutrition.uncertainties)
    assert any("Ignored detected food items: none" in item for item in nutrition.uncertainties)
    assert any("100 g" in item for item in nutrition.uncertainties)


def test_multiple_items_mix_usda_and_local_reference_with_requested_serving(
    monkeypatch,
):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            match = (
                usda_food("Paneer", 265, protein=18.3, carbs=1.2, fat=20.8, fiber=0, sugar=1.2)
                if params["query"] == "paneer"
                else None
            )
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"foods": [match] if match else []},
            )

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", FakeAsyncClient)

    nutrition, score, _label, _reasoning, _insights, _alternatives = asyncio.run(
        estimate_nutrition(
            "vegetable paneer plate",
            ["paneer", "rice"],
            serving_size_g=300,
        )
    )

    # Paneer: 100 g USDA; rice: 158 g local. Their combined 258 g is
    # scaled to 300 g, preserving their relative reference portions.
    expected_calories = round((265 + 130 * 1.58) * 300 / 258, 1)
    assert nutrition.calories_kcal == expected_calories
    assert nutrition.serving_size_g == 300
    assert nutrition.serving_size_is_assumed is True
    assert "requested serving weight" in nutrition.serving_description
    assert score is not None
    assert any("paneer, rice" in item for item in nutrition.uncertainties)
    assert any("Ignored detected food items: none" in item for item in nutrition.uncertainties)


def test_multiple_item_coverage_below_60_percent_withholds_nutrition_and_score(
    monkeypatch,
):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            match = (
                usda_food("Rice", 130)
                if params["query"] == "rice"
                else None
            )
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"foods": [match] if match else []},
            )

    monkeypatch.setattr(nutrition_estimation.httpx, "AsyncClient", FakeAsyncClient)

    nutrition, score, label, reasoning, *_ = asyncio.run(
        estimate_nutrition(
            "mixed food platter",
            ["rice", "mystery sauce", "unlisted vegetable"],
        )
    )

    assert nutrition.calories_kcal is None
    assert nutrition.protein_g is None
    assert score is None
    assert label is None
    assert "33%" in reasoning
    assert any("Matched detected food items: rice" in item for item in nutrition.uncertainties)
    assert any(
        "Ignored detected food items: mystery sauce, unlisted vegetable" in item
        for item in nutrition.uncertainties
    )


def test_garnishes_are_excluded_from_weight_coverage(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, score, label, _reasoning, *_ = asyncio.run(
        estimate_nutrition("rice with garnish", ["rice", "cilantro"])
    )

    assert nutrition.calories_kcal is not None
    assert score is not None
    assert label is not None
    assert any("Ignored detected food items: cilantro" in item for item in nutrition.uncertainties)


def test_weight_coverage_passes_when_one_large_local_portion_matches(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, score, label, _reasoning, *_ = asyncio.run(
        estimate_nutrition("unknown combination", ["dal", "unknown food"])
    )

    # Dal's 200 g reference serving covers 200/300 g, despite only one
    # of two detected items having a reference.
    assert nutrition.calories_kcal is not None
    assert score is not None
    assert label is not None
    assert any("Matched detected food items: dal" in item for item in nutrition.uncertainties)


def test_weight_coverage_fails_when_count_coverage_would_pass(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")

    nutrition, score, label, reasoning, *_ = asyncio.run(
        estimate_nutrition(
            "unknown combination",
            ["roti", "boiled egg", "unknown food"],
        )
    )

    # Two of three foods match, but their 40 g and 50 g servings cover
    # only 90/190 g of estimated portions.
    assert nutrition.calories_kcal is None
    assert score is None
    assert label is None
    assert "47%" in reasoning


def test_stuffed_item_rejects_usda_match_without_exact_local_reference(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")
    requested_items = []

    async def fake_usda_lookup(item):
        requested_items.append(item)
        if item == "rice":
            return "USDA rice", usda_food("USDA rice", 130)
        return None

    monkeypatch.setattr(nutrition_estimation, "_fetch_usda_food", fake_usda_lookup)
    monkeypatch.setattr(nutrition_estimation, "_find_local_food", lambda _item: None)

    nutrition, score, _label, _reasoning, *_ = asyncio.run(
        estimate_nutrition("unknown dish", ["stuffed peppers", "rice"])
    )

    assert "stuffed peppers" not in requested_items
    assert nutrition.calories_kcal is None
    assert score is None
    assert any(
        "Ignored detected food items: stuffed peppers" in item
        for item in nutrition.uncertainties
    )


def test_stuffed_item_uses_exact_local_reference_without_usda_lookup(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "test-key")
    local_entry = {
        "aliases": ("stuffed peppers",),
        "default_serving_g": 150.0,
        "calories_kcal": 120.0,
        "protein_g": 5.0,
        "carbs_g": 15.0,
        "fats_g": 4.0,
        "fiber_g": 3.0,
        "sugar_g": 5.0,
    }
    requested_items = []

    def fake_local_lookup(item):
        if item == "stuffed peppers":
            return "stuffed peppers", local_entry
        return None

    async def fake_usda_lookup(item):
        requested_items.append(item)
        return None

    monkeypatch.setattr(nutrition_estimation, "_find_local_food", fake_local_lookup)
    monkeypatch.setattr(nutrition_estimation, "_fetch_usda_food", fake_usda_lookup)

    nutrition, score, _label, _reasoning, *_ = asyncio.run(
        estimate_nutrition("unknown dish", ["stuffed peppers", "rice"])
    )

    assert "stuffed peppers" not in requested_items
    assert nutrition.calories_kcal is not None
    assert score is not None
    assert any(
        "Matched detected food items: stuffed peppers" in item
        for item in nutrition.uncertainties
    )
