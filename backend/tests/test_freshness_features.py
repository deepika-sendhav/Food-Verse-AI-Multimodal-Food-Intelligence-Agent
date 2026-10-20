import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import freshness
from backend.schemas import FreshnessFeatures
from backend.services.freshness_features import (
    extract_freshness_features,
    validate_features,
)
from backend.services.image_processing import InvalidImageError

client = TestClient(app)


def encode_rgb(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(
        ".png",
        cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
    )
    assert success
    return encoded.tobytes()


def uniform_green() -> np.ndarray:
    return np.full((128, 128, 3), (60, 150, 70), dtype=np.uint8)


def test_uniform_green_has_high_color_consistency_and_smoothness():
    features = extract_freshness_features(encode_rgb(uniform_green()))

    assert features.color.consistency_score > 0.9
    assert features.texture.smoothness_score > 0.9
    assert len(features.color.dominant_colors) == 3
    assert validate_features(features) == []


def test_noisy_image_has_lower_smoothness_than_uniform_image():
    rng = np.random.default_rng(42)
    noisy = np.clip(
        uniform_green().astype(np.int16)
        + rng.normal(0, 45, (128, 128, 3)).astype(np.int16),
        0,
        255,
    ).astype(np.uint8)

    clean_features = extract_freshness_features(encode_rgb(uniform_green()))
    noisy_features = extract_freshness_features(encode_rgb(noisy))

    assert noisy_features.texture.smoothness_score < clean_features.texture.smoothness_score


def test_brown_patches_raise_discoloration_fraction():
    clean = uniform_green()
    patched = clean.copy()
    patched[24:104, 24:104] = (80, 40, 20)

    clean_features = extract_freshness_features(encode_rgb(clean))
    patched_features = extract_freshness_features(encode_rgb(patched))

    assert patched_features.yellow_brown_fraction > clean_features.yellow_brown_fraction


def test_color_consistency_is_similar_after_brightness_changes():
    base = uniform_green()
    bright = np.clip(base.astype(np.float32) * 1.25, 0, 255).astype(np.uint8)
    dark = np.clip(base.astype(np.float32) * 0.65, 0, 255).astype(np.uint8)

    base_score = extract_freshness_features(encode_rgb(base)).color.consistency_score
    bright_score = extract_freshness_features(encode_rgb(bright)).color.consistency_score
    dark_score = extract_freshness_features(encode_rgb(dark)).color.consistency_score

    assert abs(base_score - bright_score) <= 0.05
    assert abs(base_score - dark_score) <= 0.05


def test_corrupt_image_raises_invalid_image_error():
    with pytest.raises(InvalidImageError):
        extract_freshness_features(b"not an image")


def test_validate_features_reports_invalid_range():
    features = extract_freshness_features(encode_rgb(uniform_green()))
    invalid = features.model_copy(
        update={"dark_discoloration_fraction": 1.5}
    )

    assert any(
        "dark_discoloration_fraction" in problem
        for problem in validate_features(invalid)
    )


def test_freshness_endpoint_returns_structured_features(monkeypatch):
    monkeypatch.setattr(freshness, "MAX_UPLOAD_SIZE_BYTES", 1024 * 1024)
    response = client.post(
        "/api/freshness/features",
        files={"file": ("green.png", encode_rgb(uniform_green()), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feature_version"] == "1.0"
    assert payload["color"]["consistency_score"] > 0.9
    assert payload["quality_flags"]["too_dark"] is False


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "status_code"),
    [
        ("green.gif", "image/png", encode_rgb(uniform_green()), 415),
        ("green.png", "image/png", b"not an image", 422),
        ("empty.png", "image/png", b"", 400),
    ],
)
def test_freshness_endpoint_upload_errors(
    filename,
    content_type,
    content,
    status_code,
):
    response = client.post(
        "/api/freshness/features",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == status_code
