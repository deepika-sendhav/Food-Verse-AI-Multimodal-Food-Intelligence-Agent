import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import freshness
from backend.schemas import (
    FreshnessAnalysisResponse,
    FreshnessRuleAssessment,
    SurfacePatternFeatures,
)
from backend.services.freshness_assessment import (
    assess_freshness_rules,
    combine_freshness_assessment,
)
from backend.services.freshness_classifier import (
    FreshnessModelResult,
    ModelTimeoutError,
)
from backend.services.freshness_features import extract_freshness_features

client = TestClient(app)


def encode_rgb(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(
        ".png",
        cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
    )
    assert success
    return encoded.tobytes()


def make_image(color=(60, 150, 70)) -> bytes:
    return encode_rgb(np.full((128, 128, 3), color, dtype=np.uint8))


def post_analysis(image: bytes, **form_data):
    return client.post(
        "/api/freshness/analyze",
        files={"file": ("food.png", image, "image/png")},
        data=form_data,
    )


def model_result(level="fresh", item_name="green vegetable"):
    return FreshnessModelResult(
        item_name=item_name,
        freshness_level=level,
        detected_signs=[],
        reasoning=f"The visible food appears {level.replace('_', ' ')}.",
    )


def test_fresh_synthetic_image_returns_fresh_and_valid_schema(monkeypatch):
    async def classify(_image, _features, **_context):
        return model_result()

    monkeypatch.setattr(freshness, "classify_freshness", classify)
    response = post_analysis(make_image())

    assert response.status_code == 200
    result = FreshnessAnalysisResponse.model_validate(response.json())
    assert result.success is True
    assert result.freshness_level == "fresh"
    assert result.confidence <= 90
    assert result.safety_disclaimer == (
        "This is a visual estimate, not a food safety guarantee. When in doubt, throw it out."
    )


def test_brown_patch_image_has_lower_rule_score():
    clean = make_image()
    patched = np.full((128, 128, 3), (60, 150, 70), dtype=np.uint8)
    patched[24:104, 24:104] = (80, 40, 20)

    clean_score = assess_freshness_rules(extract_freshness_features(clean)).score
    patched_score = assess_freshness_rules(
        extract_freshness_features(encode_rgb(patched))
    ).score

    assert patched_score < clean_score


def test_model_uncertain_produces_uncertain_final_level():
    features = extract_freshness_features(make_image())
    result = combine_freshness_assessment(
        features,
        assess_freshness_rules(features),
        model_result("uncertain"),
    )

    assert result.freshness_level == "uncertain"


def test_two_level_disagreement_is_uncertain_unless_mold_is_strong():
    features = extract_freshness_features(make_image())
    rules = FreshnessRuleAssessment(score=85, signals=["clean rule signals"])
    model_spoiled = model_result("spoiled")

    uncertain = combine_freshness_assessment(features, rules, model_spoiled)
    mold_features = features.model_copy(
        update={
            "surface_patterns": SurfacePatternFeatures(
                edge_density=features.surface_patterns.edge_density,
                mold_like_pattern_fraction=0.02,
            )
        }
    )
    cautious = combine_freshness_assessment(mold_features, rules, model_spoiled)

    assert uncertain.freshness_level == "uncertain"
    assert cautious.freshness_level == "spoiled"


def test_confidence_is_capped_and_reduced_for_dark_image():
    bright_features = extract_freshness_features(make_image((100, 180, 100)))
    dark_features = extract_freshness_features(make_image((8, 15, 8)))
    bright = combine_freshness_assessment(
        bright_features,
        assess_freshness_rules(bright_features),
        model_result(),
    )
    dark = combine_freshness_assessment(
        dark_features,
        assess_freshness_rules(dark_features),
        model_result(),
    )

    assert bright.confidence <= 90
    assert dark.confidence <= 90
    assert dark.confidence < bright.confidence


def test_storage_context_adds_specific_warning():
    features = extract_freshness_features(make_image())
    result = combine_freshness_assessment(
        features,
        assess_freshness_rules(features),
        model_result(item_name="chicken"),
        storage_time="3 hours",
        storage_type="room temperature",
    )

    assert any("exceeds two hours" in warning for warning in result.safety_warnings)
    assert any("time-temperature control" in warning for warning in result.safety_warnings)


def test_groq_timeout_returns_rules_only_assessment(monkeypatch):
    async def timed_out(*_args, **_kwargs):
        raise ModelTimeoutError

    monkeypatch.setattr(freshness, "classify_freshness", timed_out)
    response = post_analysis(make_image())

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["item_name"] is None
    assert any("timed out" in note for note in payload["uncertainties"])


def test_invalid_image_has_same_error_on_features_and_analyze():
    files = {"file": ("bad.png", b"not an image", "image/png")}
    features_response = client.post("/api/freshness/features", files=files)
    analyze_response = client.post("/api/freshness/analyze", files=files)

    assert analyze_response.status_code == features_response.status_code == 422
    assert analyze_response.json()["detail"] == features_response.json()["detail"]
