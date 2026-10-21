import gc
import io
import json
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import (
    food_recognition,
    freshness,
    hygiene,
    kitchen_assistant,
    meal_planner,
)
from backend.schemas import (
    FoodAnalysisResponse,
    FreshnessAnalysisResponse,
    FreshnessFeatures,
    HygieneAnalysisResponse,
    MealPlanResponse,
    RecipeGenerationResponse,
    UserProfileInput,
)
from backend.services.demo_responses import DEMO_DATA_DIR, load_demo_response
from backend.services.freshness_assessment import assess_freshness_rules
from backend.services.freshness_features import extract_freshness_features
from backend.services.nutrition_targets import compute_nutrition_targets
from backend.services.user_profile import InMemoryProfileRepository, normalize_profile

DEMO_SCHEMAS = {
    "food_recognition": FoodAnalysisResponse,
    "freshness": FreshnessAnalysisResponse,
    "freshness_features": FreshnessFeatures,
    "hygiene": HygieneAnalysisResponse,
    "kitchen_assistant": RecipeGenerationResponse,
    "meal_plan": MealPlanResponse,
    "safety_gate": MealPlanResponse,
}
client = TestClient(app)


def test_every_demo_file_validates_against_its_real_schema():
    files = {path.stem for path in DEMO_DATA_DIR.glob("*.json")}
    assert files == set(DEMO_SCHEMAS)
    for name, schema in DEMO_SCHEMAS.items():
        payload = json.loads((DEMO_DATA_DIR / f"{name}.json").read_text())
        schema.model_validate(payload)
        if name not in {"freshness_features"}:
            sample = load_demo_response(name, schema)
            assert sample.demo is True
            assert sample.demo_warning


def test_demo_mode_returns_labeled_samples_without_model_calls(monkeypatch):
    monkeypatch.setattr(food_recognition, "DEMO_MODE", True)
    monkeypatch.setattr(freshness, "DEMO_MODE", True)
    monkeypatch.setattr(hygiene, "DEMO_MODE", True)
    monkeypatch.setattr(kitchen_assistant, "DEMO_MODE", True)
    monkeypatch.setattr(meal_planner, "DEMO_MODE", True)
    repository = InMemoryProfileRepository()
    profile = normalize_profile(
        UserProfileInput.model_validate(
            {
                "age_years": 30,
                "sex": "female",
                "height": 165,
                "height_unit": "cm",
                "weight": 60,
                "weight_unit": "kg",
                "activity_level": "moderate",
                "health_goal": "maintain",
                "diet_type": "omnivore",
            }
        )
    )
    repository.save(profile)
    monkeypatch.setattr(meal_planner, "profile_repository", repository)
    sample_image = io.BytesIO()
    Image.new("RGB", (8, 8), color=(80, 120, 45)).save(sample_image, format="JPEG")
    image_bytes = sample_image.getvalue()

    requests = [
        client.post(
            "/api/food-recognition/analyze",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        ),
        client.post(
            "/api/freshness/analyze",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        ),
        client.post(
            "/api/freshness/features",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        ),
        client.post(
            "/api/hygiene/analyze",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
        ),
        client.post(
            "/api/kitchen/generate-recipe",
            data={"text_input": "synthetic sample input"},
        ),
        client.post(
            "/api/meal-plan/generate",
            json={"profile_id": str(profile.profile_id)},
        ),
    ]

    for response in requests:
        assert response.status_code == 200
    for response in (requests[0], requests[1], requests[3], requests[4], requests[5]):
        assert response.json()["demo"] is True
        assert "sample data only" in response.json()["demo_warning"]
    assert requests[2].json()["feature_version"] == "demo-1"


def test_health_reports_demo_and_missing_model_configuration(monkeypatch):
    import backend.main

    monkeypatch.setattr(backend.main, "DEMO_MODE", True)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["demo"] is True
    assert response.json()["configured"] is False
    assert "sample data only" in response.json()["demo_warning"]


def test_rule_based_pipelines_are_deterministic_over_repeated_runs():
    image = Image.new("RGB", (32, 32))
    image.putdata(
        [
            ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
            for y in range(32)
            for x in range(32)
        ]
    )
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    image_bytes = encoded.getvalue()
    profile_input = UserProfileInput.model_validate(
        {
            "age_years": 34,
            "sex": "female",
            "height": 168,
            "height_unit": "cm",
            "weight": 70,
            "weight_unit": "kg",
            "activity_level": "light",
            "health_goal": "maintain",
            "diet_type": "vegetarian",
            "allergies": ["peanut"],
        }
    )

    def run_pipeline():
        features = extract_freshness_features(image_bytes)
        assessment = assess_freshness_rules(features)
        profile = normalize_profile(
            profile_input,
            profile_id=UUID(int=1),
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        targets = compute_nutrition_targets(profile)
        return {
            "features": features.model_dump(mode="json"),
            "assessment": assessment.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json"),
            "targets": targets.model_dump(mode="json"),
        }

    expected = run_pipeline()
    gc.collect()
    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()
    for _ in range(100):
        assert run_pipeline() == expected
    gc.collect()
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert current - baseline < 512 * 1024
