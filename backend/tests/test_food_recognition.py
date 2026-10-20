import json
from io import BytesIO
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient
from groq import APITimeoutError
import pytest

from backend.main import app
from backend.routers import food_recognition
from backend.schemas import FoodAnalysisResponse, FoodModelResult
from backend.services import food_classifier
from backend.services import nutrition_estimation

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_usda_requests(monkeypatch):
    monkeypatch.setattr(nutrition_estimation, "USDA_FDC_API_KEY", "")


def make_png() -> bytes:
    from PIL import Image

    image = Image.new("RGB", (48, 32), color=(180, 90, 40))
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    return output.getvalue()


def post_image(
    content: bytes,
    filename: str = "meal.png",
    content_type: str = "image/png",
):
    return client.post(
        "/api/food-recognition/analyze",
        files={"file": (filename, content, content_type)},
    )


def mock_groq(monkeypatch, payload=None, error=None):
    captured_requests = []

    class FakeAsyncGroq:
        def __init__(self, **kwargs):
            self.client_options = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def create_completion(self, **kwargs):
            captured_requests.append((self.client_options, kwargs))
            if error:
                raise error
            message = SimpleNamespace(content=json.dumps(payload))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)]
            )

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(food_classifier, "AsyncGroq", FakeAsyncGroq)
    return captured_requests


def test_valid_food_image_is_classified(monkeypatch):
    captured = mock_groq(
        monkeypatch,
        {
            "dish_name": "Vegetable curry",
            "detected_items": ["curry", "rice"],
            "description": "A bowl of curry served with rice.",
            "uncertainties": [],
        },
    )
    response = post_image(make_png())

    assert response.status_code == 200
    assert response.json()["dish_name"] == "Vegetable curry"
    assert response.json()["detected_items"] == ["curry", "rice"]
    assert response.json()["confidence"] is None
    client_options, request = captured[0]
    assert client_options["max_retries"] == 0
    assert request["model"] == food_classifier.GROQ_VISION_MODEL
    image_content = request["messages"][0]["content"][1]["image_url"]["url"]
    assert image_content.startswith("data:image/jpeg;base64,")
    prompt = request["messages"][0]["content"][0]["text"].casefold()
    assert "edible food" in prompt
    assert 'use simple, consistent names for items (for example "green chili"' in prompt
    assert 'not "stuffed pepper" or "stuffed green chili"' in prompt
    assert "list side garnishes such as chili, lime, onion, and cilantro as separate items" in prompt
    assert "lime, onion, and cilantro" in prompt
    assert "never include utensils, plates, bowls" in prompt


def test_detected_items_excludes_tableware_and_other_objects(monkeypatch):
    mock_groq(
        monkeypatch,
        {
            "dish_name": "Rice and dal",
            "detected_items": ["rice", "plate", "steel bowl", "fork", "dal", "napkin"],
            "description": "Rice and dal served together.",
            "uncertainties": [],
        },
    )

    response = post_image(make_png())

    assert response.status_code == 200
    assert response.json()["detected_items"] == ["rice", "dal"]


def test_detected_items_use_simple_names_and_separate_garnishes(monkeypatch):
    result = FoodModelResult(
        dish_name="Stuffed green chili",
        detected_items=[
            "Stuffed Green Chili",
            "Lime",
            "Onion",
            "Cilantro",
        ],
        description="A stuffed green chili with garnish.",
        uncertainties=[],
    )

    assert result.detected_items == ["green chili", "lime", "onion", "cilantro"]


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("meal.gif", "image/png"), ("meal.png", "text/plain")],
)
def test_rejects_unsupported_extension_or_mime_type(filename, content_type):
    response = post_image(make_png(), filename=filename, content_type=content_type)

    assert response.status_code == 415


def test_rejects_corrupted_image():
    response = post_image(b"this is not an image")

    assert response.status_code == 422


def test_rejects_empty_upload():
    response = post_image(b"")

    assert response.status_code == 400


def test_rejects_image_over_configured_size(monkeypatch):
    monkeypatch.setattr(food_recognition, "MAX_UPLOAD_SIZE_BYTES", 10)
    response = post_image(make_png())

    assert response.status_code == 413


def test_maps_model_timeout_to_gateway_timeout(monkeypatch):
    mock_groq(
        monkeypatch,
        error=APITimeoutError(
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        ),
    )
    response = post_image(make_png())

    assert response.status_code == 504


def test_ambiguous_model_result_is_successful_without_guessing(monkeypatch):
    mock_groq(
        monkeypatch,
        {
            "dish_name": None,
            "detected_items": [],
            "description": "The image is too unclear to identify the food.",
            "uncertainties": ["The dish is obscured and out of focus."],
        },
    )
    response = post_image(make_png())

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["dish_name"] is None
    assert response.json()["uncertainties"]


def test_successful_response_validates_against_schema(monkeypatch):
    mock_groq(
        monkeypatch,
        {
            "dish_name": "Soup",
            "detected_items": ["soup"],
            "description": "A bowl of soup.",
            "uncertainties": [],
        },
    )
    response = post_image(make_png())

    assert response.status_code == 200
    validated = FoodAnalysisResponse.model_validate(response.json())
    assert validated.success is True
    assert validated.confidence is None
    assert validated.nutrition.serving_size_g is None


def test_serving_size_can_be_supplied_as_multipart_form_field(monkeypatch):
    async def classify(_image_bytes):
        return FoodModelResult(
            dish_name="banana",
            detected_items=["banana"],
            description="A banana.",
            uncertainties=[],
        )

    monkeypatch.setattr(food_recognition, "classify_food", classify)
    response = client.post(
        "/api/food-recognition/analyze",
        files={"file": ("banana.png", make_png(), "image/png")},
        data={"serving_size_g": "200"},
    )

    assert response.status_code == 200
    assert response.json()["nutrition"]["serving_size_g"] == 200
    assert response.json()["nutrition"]["serving_size_is_assumed"] is False
