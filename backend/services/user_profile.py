import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
from uuid import UUID, uuid4

from backend.config import PROFILE_TTL_MINUTES
from backend.schemas import (
    CanonicalAllergen,
    ExcludedFood,
    ProfileSafetyFlag,
    UserProfile,
    UserProfileInput,
)


CANONICAL_ALLERGENS: tuple[CanonicalAllergen, ...] = (
    "milk",
    "egg",
    "peanut",
    "tree_nuts",
    "wheat_gluten",
    "soy",
    "fish",
    "shellfish",
    "sesame",
    "mustard",
    "celery",
    "sulphites",
)


def _normalize(value: str) -> str:
    return re.sub(r"[\W_]+", " ", value.casefold()).strip()


ALLERGEN_SYNONYMS: dict[CanonicalAllergen, tuple[str, ...]] = {
    "milk": ("milk", "dairy", "lactose", "curd", "paneer", "cheese", "yogurt", "yoghurt", "butter", "ghee"),
    "egg": ("egg", "eggs"),
    "peanut": ("peanut", "peanuts", "groundnut", "groundnuts"),
    "tree_nuts": ("tree nuts", "almond", "cashew", "walnut", "pistachio", "pecan", "hazelnut"),
    "wheat_gluten": ("wheat", "gluten", "maida", "atta", "flour", "semolina", "suji", "sooji"),
    "soy": ("soy", "soya", "soybean", "tofu"),
    "fish": ("fish",),
    "shellfish": ("shellfish", "prawn", "prawns", "shrimp", "crab", "lobster", "crayfish"),
    "sesame": ("sesame", "til", "tahini"),
    "mustard": ("mustard",),
    "celery": ("celery",),
    "sulphites": ("sulphite", "sulphites", "sulfite", "sulfites"),
}

DIET_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "omnivore": (),
    "vegetarian": ("meat", "poultry", "fish", "shellfish", "gelatin"),
    "vegan": ("meat", "poultry", "fish", "shellfish", "gelatin", "milk", "egg", "honey"),
    "pescatarian": ("meat", "poultry"),
    "eggetarian": ("meat", "poultry", "fish", "shellfish"),
    "jain": (
        "meat", "poultry", "fish", "shellfish", "egg",
        "root vegetables", "onion", "garlic", "potato", "carrot",
    ),
    "halal": ("pork", "alcohol"),
    "kosher": ("pork", "shellfish"),
    "other": (),
}

_CANONICAL_BY_SYNONYM = {
    _normalize(value): canonical
    for canonical, synonyms in ALLERGEN_SYNONYMS.items()
    for value in (canonical, *synonyms)
}
_OPTIONAL_FIELDS = (
    "allergies",
    "food_restrictions",
    "dislikes",
    "medical_conditions",
    "pregnant_or_breastfeeding",
    "meals_per_day",
    "cuisine_preferences",
)
_EATING_DISORDER_TERMS = (
    "eating disorder",
    "anorexia",
    "bulimia",
    "binge eating",
)


class ProfileValidationError(Exception):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("Profile values failed validation.")
        self.errors = errors


class ProfileCapacityError(Exception):
    pass


class ProfileRepository(Protocol):
    def save(self, profile: UserProfile) -> None: ...
    def get(self, profile_id: UUID) -> UserProfile | None: ...
    def replace(self, profile: UserProfile) -> bool: ...
    def delete(self, profile_id: UUID) -> bool: ...


class InMemoryProfileRepository:
    def __init__(
        self,
        *,
        max_profiles: int = 1000,
        ttl_minutes: int = PROFILE_TTL_MINUTES,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._max_profiles = max_profiles
        self._ttl = timedelta(minutes=ttl_minutes)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._profiles: dict[UUID, tuple[UserProfile, datetime]] = {}
        self._lock = threading.RLock()

    def _purge_expired(self, now: datetime) -> None:
        expired = [
            profile_id
            for profile_id, (_, stored_at) in self._profiles.items()
            if now - stored_at >= self._ttl
        ]
        for profile_id in expired:
            del self._profiles[profile_id]

    def save(self, profile: UserProfile) -> None:
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            if len(self._profiles) >= self._max_profiles:
                raise ProfileCapacityError
            self._profiles[profile.profile_id] = (profile.model_copy(deep=True), now)

    def get(self, profile_id: UUID) -> UserProfile | None:
        with self._lock:
            self._purge_expired(self._clock())
            stored = self._profiles.get(profile_id)
            return stored[0].model_copy(deep=True) if stored else None

    def replace(self, profile: UserProfile) -> bool:
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            if profile.profile_id not in self._profiles:
                return False
            self._profiles[profile.profile_id] = (profile.model_copy(deep=True), now)
            return True

    def delete(self, profile_id: UUID) -> bool:
        with self._lock:
            self._purge_expired(self._clock())
            return self._profiles.pop(profile_id, None) is not None


profile_repository: ProfileRepository = InMemoryProfileRepository()


def _normalized_allergy(value: str) -> CanonicalAllergen | None:
    return _CANONICAL_BY_SYNONYM.get(_normalize(value))


def _contains_term(text: str, term: str) -> bool:
    return f" {_normalize(term)} " in f" {_normalize(text)} "


def _append_unique_warning(warnings: list[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)


def _build_safety_flags(data: UserProfileInput, bmi: float) -> list[ProfileSafetyFlag]:
    flags: list[ProfileSafetyFlag] = []
    if data.age_years < 18:
        flags.append(
            ProfileSafetyFlag(
                code="under_18",
                message="A doctor or dietitian should guide nutrition decisions for people under 18; avoid restrictive plans.",
                severity="consult_professional",
            )
        )
    if data.pregnant_or_breastfeeding is True:
        flags.append(
            ProfileSafetyFlag(
                code="pregnancy_or_breastfeeding",
                message="A healthcare professional can provide individualized nutrition guidance during pregnancy or breastfeeding.",
                severity="consult_professional",
            )
        )
    if bmi < 18.5:
        flags.append(
            ProfileSafetyFlag(
                code="low_bmi",
                message="Consider discussing nutrition goals with a healthcare professional.",
                severity="consult_professional",
            )
        )
    if data.medical_conditions:
        eating_disorder_mentioned = any(
            _contains_term(condition, term)
            for condition in data.medical_conditions
            for term in _EATING_DISORDER_TERMS
        )
        message = (
            "Consider speaking with a healthcare professional for supportive guidance."
            if eating_disorder_mentioned
            else "A healthcare professional can help account for health conditions when discussing nutrition."
        )
        flags.append(
            ProfileSafetyFlag(
                code="medical_conditions",
                message=message,
                severity="consult_professional",
            )
        )
    if data.health_goal == "lose_weight" and flags:
        flags.append(
            ProfileSafetyFlag(
                code="weight_goal_with_safety_factors",
                message="Please discuss this goal with a healthcare professional before pursuing restrictive changes.",
                severity="consult_professional",
            )
        )
    return flags


def normalize_profile(
    data: UserProfileInput,
    *,
    profile_id: UUID | None = None,
    created_at: datetime | None = None,
) -> UserProfile:
    height_cm = data.height * 2.54 if data.height_unit == "in" else data.height
    weight_kg = data.weight * 0.45359237 if data.weight_unit == "lb" else data.weight
    invalid_ranges = []
    if not 100 <= height_cm <= 250:
        invalid_ranges.append(
            {"field": "height", "message": "Height must be between 100 and 250 cm after unit conversion."}
        )
    if not 25 <= weight_kg <= 300:
        invalid_ranges.append(
            {"field": "weight", "message": "Weight must be between 25 and 300 kg after unit conversion."}
        )
    if invalid_ranges:
        raise ProfileValidationError(invalid_ranges)

    height_cm = round(height_cm, 2)
    weight_kg = round(weight_kg, 2)
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    warnings: list[str] = []
    allergens: list[CanonicalAllergen] = []
    unrecognized: list[str] = []
    seen_allergies: set[str] = set()
    for allergy in data.allergies:
        canonical = _normalized_allergy(allergy)
        key = canonical or _normalize(allergy)
        if key in seen_allergies:
            _append_unique_warning(warnings, "Duplicate allergy entries were provided.")
            continue
        seen_allergies.add(key)
        if canonical:
            allergens.append(canonical)
        else:
            unrecognized.append(allergy)
            _append_unique_warning(
                warnings,
                "One or more allergies could not be matched to a known allergen and will remain strict exclusions.",
            )

    if data.health_goal == "lose_weight" and bmi < 18.5:
        _append_unique_warning(
            warnings,
            "The weight-loss goal conflicts with the supplied BMI information; review this goal with a professional.",
        )
    if data.health_goal == "gain_weight" and bmi > 30:
        _append_unique_warning(
            warnings,
            "The weight-gain goal conflicts with the supplied BMI information; review this goal with a professional.",
        )

    exclusions: list[ExcludedFood] = []
    seen_exclusions: dict[str, ExcludedFood] = {}

    def add_exclusion(name: str, reason: str, strict: bool) -> None:
        key = _normalize(name)
        existing = seen_exclusions.get(key)
        if existing is not None:
            if existing.reason != reason:
                _append_unique_warning(
                    warnings,
                    "Some foods appear in more than one exclusion category.",
                )
            priorities = {"allergy": 0, "diet": 1, "restriction": 2, "dislike": 3}
            if priorities[reason] < priorities[existing.reason]:
                existing.reason = reason
                existing.strict = strict
            return
        exclusion = ExcludedFood(name=name, reason=reason, strict=strict)
        seen_exclusions[key] = exclusion
        exclusions.append(exclusion)

    for allergen in allergens:
        add_exclusion(allergen, "allergy", True)
    for allergy in unrecognized:
        add_exclusion(allergy, "allergy", True)
    for food in DIET_EXCLUSIONS[data.diet_type]:
        add_exclusion(food, "diet", True)
    for restriction in data.food_restrictions:
        add_exclusion(restriction, "restriction", True)
    for dislike in data.dislikes:
        add_exclusion(dislike, "dislike", False)

    for preference in data.cuisine_preferences:
        matching_allergy = next(
            (
                allergy
                for allergy in data.allergies
                if _contains_term(preference, allergy)
                or _normalized_allergy(preference) == _normalized_allergy(allergy)
                and _normalized_allergy(allergy) is not None
            ),
            None,
        )
        matching_diet_food = next(
            (
                food
                for food in DIET_EXCLUSIONS[data.diet_type]
                if _contains_term(preference, food)
                or (
                    _normalized_allergy(preference) is not None
                    and _normalized_allergy(preference) == _normalized_allergy(food)
                )
            ),
            None,
        )
        if matching_allergy or matching_diet_food:
            _append_unique_warning(
                warnings,
                "A cuisine preference may conflict with an allergy or the selected diet type; review it before use.",
            )

    values_by_category = {
        "allergies": data.allergies,
        "food_restrictions": data.food_restrictions,
        "dislikes": data.dislikes,
        "cuisine_preferences": data.cuisine_preferences,
    }
    normalized_values: set[str] = set()
    has_duplicates = False
    for values in values_by_category.values():
        for value in values:
            key = _normalize(value)
            if key in normalized_values:
                has_duplicates = True
            normalized_values.add(key)
    if has_duplicates:
        _append_unique_warning(warnings, "Duplicate or overlapping food preferences were provided.")

    safety_flags = _build_safety_flags(data, bmi)
    optional_provided = sum(field in data.model_fields_set for field in _OPTIONAL_FIELDS)
    completeness = round(optional_provided / len(_OPTIONAL_FIELDS) * 100, 1)
    return UserProfile(
        profile_id=profile_id or uuid4(),
        created_at=created_at or datetime.now(timezone.utc),
        age_years=data.age_years,
        sex=data.sex,
        height=data.height,
        height_unit=data.height_unit,
        weight=data.weight,
        weight_unit=data.weight_unit,
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi,
        activity_level=data.activity_level,
        health_goal=data.health_goal,
        diet_type=data.diet_type,
        meals_per_day=data.meals_per_day,
        cuisine_preferences=data.cuisine_preferences,
        food_restrictions=data.food_restrictions,
        dislikes=data.dislikes,
        allergens=allergens,
        unrecognized_allergies=unrecognized,
        excluded_foods=exclusions,
        medical_conditions=data.medical_conditions or [],
        pregnant_or_breastfeeding=data.pregnant_or_breastfeeding,
        safety_flags=safety_flags,
        requires_professional_review=any(
            flag.severity == "consult_professional" for flag in safety_flags
        ),
        warnings=warnings,
        completeness_score=completeness,
    )
