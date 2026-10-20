import logging
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import UserProfile, UserProfileInput
from backend.services import user_profile
from backend.services.user_profile import (
    InMemoryProfileRepository,
    ProfileValidationError,
    normalize_profile,
)

client = TestClient(app)


def profile_payload(**updates):
    payload = {
        "age_years": 30,
        "sex": "prefer_not_to_say",
        "height": 170,
        "height_unit": "cm",
        "weight": 68,
        "weight_unit": "kg",
        "activity_level": "moderate",
        "health_goal": "maintain",
        "diet_type": "omnivore",
    }
    payload.update(updates)
    return payload


def validate(payload):
    return normalize_profile(UserProfileInput.model_validate(payload))


@pytest.mark.parametrize(
    ("height", "height_unit", "expected_cm", "weight", "weight_unit", "expected_kg"),
    [
        (65, "in", 165.1, 150, "lb", 68.04),
        (180, "cm", 180, 100, "kg", 100),
    ],
)
def test_units_are_converted_and_original_values_preserved(
    height, height_unit, expected_cm, weight, weight_unit, expected_kg
):
    profile = validate(
        profile_payload(
            height=height,
            height_unit=height_unit,
            weight=weight,
            weight_unit=weight_unit,
        )
    )

    assert profile.height == height
    assert profile.height_unit == height_unit
    assert profile.weight == weight
    assert profile.weight_unit == weight_unit
    assert profile.height_cm == expected_cm
    assert profile.weight_kg == expected_kg


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"age_years": 12}, "age_years"),
        ({"age_years": 101}, "age_years"),
        ({"height": 99, "height_unit": "cm"}, "height"),
        ({"height": 251, "height_unit": "cm"}, "height"),
        ({"weight": 24, "weight_unit": "kg"}, "weight"),
        ({"weight": 301, "weight_unit": "kg"}, "weight"),
    ],
)
def test_out_of_range_profile_values_return_422(changes, field):
    response = client.post("/api/profile/validate", json=profile_payload(**changes))

    assert response.status_code == 422
    assert field in str(response.json()["detail"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("height", float("nan")),
        ("height", float("inf")),
        ("height", float("-inf")),
        ("weight", float("nan")),
        ("weight", float("inf")),
        ("weight", float("-inf")),
    ],
)
def test_non_finite_measurements_are_rejected(field, value):
    response = client.post(
        "/api/profile/validate",
        content=json.dumps(profile_payload(**{field: value}), allow_nan=True),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert field in str(response.json()["detail"])


def test_bmi_is_computed_as_informational_value():
    profile = validate(profile_payload(height=170, weight=68))

    assert profile.bmi == 23.5
    assert not any("diagnos" in flag.message.casefold() for flag in profile.safety_flags)


def test_allergy_synonyms_are_normalized_and_unknowns_are_strict():
    profile = validate(
        profile_payload(allergies=[" lactose ", "groundnut", "maida", "prawn", "til", "mystery pollen"])
    )

    assert profile.allergens == ["milk", "peanut", "wheat_gluten", "shellfish", "sesame"]
    assert profile.unrecognized_allergies == ["mystery pollen"]
    unknown_exclusion = next(
        item for item in profile.excluded_foods if item.name == "mystery pollen"
    )
    assert unknown_exclusion.reason == "allergy"
    assert unknown_exclusion.strict is True
    assert any("could not be matched" in warning for warning in profile.warnings)


@pytest.mark.parametrize(
    ("diet_type", "expected"),
    [
        ("vegetarian", {"meat", "poultry", "fish", "shellfish", "gelatin"}),
        ("vegan", {"milk", "egg", "honey", "meat"}),
        ("jain", {"root vegetables", "onion", "garlic", "potato", "carrot"}),
    ],
)
def test_diet_exclusion_tables_apply(diet_type, expected):
    profile = validate(profile_payload(diet_type=diet_type))
    exclusions = {item.name for item in profile.excluded_foods}

    assert expected <= exclusions
    assert all(
        item.strict
        for item in profile.excluded_foods
        if item.name in expected
    )


def test_dislikes_are_non_strict_and_duplicate_entries_warn():
    profile = validate(
        profile_payload(
            dislikes=["olives", "Olives"],
            food_restrictions=["coriander"],
        )
    )

    olives = [item for item in profile.excluded_foods if item.name.casefold() == "olives"]
    assert len(olives) == 1
    assert olives[0].reason == "dislike"
    assert olives[0].strict is False
    assert any("Duplicate" in warning for warning in profile.warnings)


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"age_years": 17}, "under_18"),
        ({"pregnant_or_breastfeeding": True}, "pregnancy_or_breastfeeding"),
        ({"height": 180, "weight": 50}, "low_bmi"),
        ({"medical_conditions": ["diabetes"]}, "medical_conditions"),
        ({"medical_conditions": ["eating disorder history"]}, "medical_conditions"),
    ],
)
def test_safety_factors_require_professional_review(changes, expected_code):
    profile = validate(profile_payload(**changes))

    assert profile.requires_professional_review is True
    assert expected_code in {flag.code for flag in profile.safety_flags}
    if changes.get("medical_conditions") == ["eating disorder history"]:
        flag = next(flag for flag in profile.safety_flags if flag.code == expected_code)
        assert "healthcare professional" in flag.message


def test_weight_goal_conflicts_and_vegan_favorite_are_warned():
    profile = validate(
        profile_payload(
            diet_type="vegan",
            cuisine_preferences=["eggs", "Thai"],
        )
    )

    assert any("conflict" in warning for warning in profile.warnings)


def test_goal_bmi_conflicts_are_reported():
    low_bmi = validate(
        profile_payload(
            height=180,
            weight=50,
            health_goal="lose_weight",
        )
    )
    high_bmi = validate(
        profile_payload(
            height=160,
            weight=100,
            health_goal="gain_weight",
        )
    )

    assert any("weight-loss goal conflicts" in warning for warning in low_bmi.warnings)
    assert any("weight-gain goal conflicts" in warning for warning in high_bmi.warnings)


def test_extra_fields_and_control_characters_are_rejected_without_echoing_data():
    extra = client.post(
        "/api/profile/validate",
        json=profile_payload(secret_health_value="private-condition"),
    )
    control = client.post(
        "/api/profile/validate",
        json=profile_payload(allergies=["private\u0000condition"]),
    )

    assert extra.status_code == 422
    assert control.status_code == 422
    assert "private" not in str(extra.json())
    assert "private" not in str(control.json())


def test_profile_crud_and_missing_profile(monkeypatch):
    repository = InMemoryProfileRepository()
    monkeypatch.setattr(user_profile, "profile_repository", repository)
    import backend.routers.profile as profile_router

    monkeypatch.setattr(profile_router, "profile_repository", repository)

    created = client.post("/api/profile", json=profile_payload())
    assert created.status_code == 201
    UserProfile.model_validate(created.json())
    profile_id = created.json()["profile_id"]
    assert UUID(profile_id)

    fetched = client.get(f"/api/profile/{profile_id}")
    assert fetched.status_code == 200
    assert fetched.json()["profile_id"] == profile_id

    updated = client.put(
        f"/api/profile/{profile_id}",
        json=profile_payload(weight=72),
    )
    assert updated.status_code == 200
    UserProfile.model_validate(updated.json())
    assert updated.json()["weight_kg"] == 72
    assert updated.json()["profile_id"] == profile_id

    deleted = client.delete(f"/api/profile/{profile_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/profile/{profile_id}").status_code == 404


def test_profile_expiry_removes_entry():
    now = datetime.now(timezone.utc)
    current_time = [now]
    repository = InMemoryProfileRepository(
        ttl_minutes=1,
        clock=lambda: current_time[0],
    )
    profile = validate(profile_payload())
    repository.save(profile)

    current_time[0] = now + timedelta(minutes=1)

    assert repository.get(profile.profile_id) is None


def test_options_endpoint_matches_allowed_values():
    response = client.get("/api/profile/options")

    assert response.status_code == 200
    options = response.json()
    assert options["sexes"] == ["female", "male", "other", "prefer_not_to_say"]
    assert options["activity_levels"] == [
        "sedentary", "light", "moderate", "active", "very_active"
    ]
    assert options["health_goals"] == [
        "maintain", "lose_weight", "gain_weight", "build_muscle", "eat_healthier"
    ]
    assert "tree_nuts" in options["canonical_allergens"]
    assert options["height_units"] == ["cm", "in"]
    assert options["weight_units"] == ["kg", "lb"]


def test_profile_logs_do_not_contain_profile_values(monkeypatch, caplog):
    repository = InMemoryProfileRepository(max_profiles=0)
    import backend.routers.profile as profile_router

    monkeypatch.setattr(profile_router, "profile_repository", repository)
    with caplog.at_level(logging.WARNING, logger=profile_router.__name__):
        response = client.post(
            "/api/profile",
            json=profile_payload(medical_conditions=["private medical condition"]),
        )

    assert response.status_code == 503
    assert "ProfileCapacityError" in caplog.text
    assert "private medical condition" not in caplog.text
    assert "profile_id=" in caplog.text
