from typing import Annotated, Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


NON_FOOD_ITEM_TERMS = {
    "bottle",
    "bowl",
    "box",
    "can",
    "container",
    "cup",
    "cutlery",
    "dishware",
    "fork",
    "mug",
    "napkin",
    "packaging",
    "plate",
    "plates",
    "pot",
    "saucer",
    "spoon",
    "table",
    "tablecloth",
    "tray",
    "utensil",
    "utensils",
}


class FoodModelResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dish_name: str | None = None
    detected_items: list[str] = Field(default_factory=list, max_length=20)
    description: str = Field(min_length=1, max_length=500)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("dish_name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("detected_items")
    @classmethod
    def keep_edible_items_only(cls, values: list[str]) -> list[str]:
        clean_values = []
        for item in values:
            cleaned = item.strip().casefold()
            if cleaned.startswith("stuffed "):
                cleaned = cleaned.removeprefix("stuffed ").strip()
            if not cleaned:
                continue
            words = set(cleaned.casefold().replace("-", " ").split())
            if words & NON_FOOD_ITEM_TERMS:
                continue
            clean_values.append(cleaned)
        return list(dict.fromkeys(clean_values))

    @field_validator("uncertainties")
    @classmethod
    def clean_uncertainties(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in values if item.strip()))


class NutritionInfo(BaseModel):
    serving_size_g: float | None = Field(default=None, gt=0)
    serving_description: str
    calories_kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fats_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    sugar_g: float | None = Field(default=None, ge=0)
    source: str
    serving_size_is_assumed: bool
    uncertainties: list[str] = Field(default_factory=list)


class FoodAnalysisResponse(BaseModel):
    success: bool
    dish_name: str | None
    detected_items: list[str]
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Null unless the provider supplies a genuine calibrated score.",
    )
    description: str
    uncertainties: list[str]
    nutrition: NutritionInfo
    health_score: int | None = Field(default=None, ge=0, le=100)
    health_label: str | None = None
    reasoning: str
    insights: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class DominantColor(BaseModel):
    red: float = Field(ge=0, le=255, allow_inf_nan=False)
    green: float = Field(ge=0, le=255, allow_inf_nan=False)
    blue: float = Field(ge=0, le=255, allow_inf_nan=False)
    percentage: float = Field(ge=0, le=100, allow_inf_nan=False)


class ColorFeatures(BaseModel):
    mean_h: float = Field(ge=0, le=179, allow_inf_nan=False)
    std_h: float = Field(ge=0, le=90, allow_inf_nan=False)
    mean_s: float = Field(ge=0, le=255, allow_inf_nan=False)
    std_s: float = Field(ge=0, le=127.5, allow_inf_nan=False)
    mean_v: float = Field(ge=0, le=255, allow_inf_nan=False)
    std_v: float = Field(ge=0, le=127.5, allow_inf_nan=False)
    dominant_colors: list[DominantColor] = Field(min_length=1, max_length=3)
    consistency_score: float = Field(ge=0, le=1, allow_inf_nan=False)


class TextureFeatures(BaseModel):
    laplacian_variance: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)
    local_standard_deviation: float = Field(ge=0, le=127.5, allow_inf_nan=False)
    smoothness_score: float = Field(ge=0, le=1, allow_inf_nan=False)


class SurfacePatternFeatures(BaseModel):
    edge_density: float = Field(ge=0, le=1, allow_inf_nan=False)
    mold_like_pattern_fraction: float = Field(ge=0, le=1, allow_inf_nan=False)


class QualityFlags(BaseModel):
    too_dark: bool
    too_bright: bool
    blurry: bool
    low_contrast: bool


class FreshnessFeatures(BaseModel):
    feature_version: str = Field(min_length=1)
    color: ColorFeatures
    dark_discoloration_fraction: float = Field(ge=0, le=1, allow_inf_nan=False)
    yellow_brown_fraction: float = Field(ge=0, le=1, allow_inf_nan=False)
    texture: TextureFeatures
    surface_patterns: SurfacePatternFeatures
    quality_flags: QualityFlags
    warnings: list[str] = Field(default_factory=list)


class FreshnessRuleAssessment(BaseModel):
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    signals: list[str] = Field(default_factory=list)


class FreshnessAnalysisResponse(BaseModel):
    success: bool
    item_name: str | None = None
    freshness_level: Literal[
        "fresh",
        "moderately_fresh",
        "spoiled",
        "uncertain",
    ]
    confidence: float = Field(ge=0, le=100, allow_inf_nan=False)
    safety_status: str
    detected_signs: list[str] = Field(default_factory=list)
    reasoning: str
    recommendation: str
    safety_warnings: list[str] = Field(default_factory=list)
    safety_disclaimer: str
    rule_assessment: FreshnessRuleAssessment
    features: FreshnessFeatures
    uncertainties: list[str] = Field(default_factory=list)
    color: Literal["green", "amber", "red", "gray"]
    alert_level: Literal["none", "info", "warning", "critical"]


HygieneIndicatorStatus = Literal[
    "compliant",
    "violation",
    "not_visible",
    "unclear",
]
HygieneIndicatorName = Literal[
    "gloves_in_use",
    "hair_covering",
    "apron_or_clean_uniform",
    "hand_to_face_or_hair_contact",
    "personal_phone_use",
    "food_contact_with_bare_hands",
    "food_on_floor_or_unsafe_storage",
    "surface_cleanliness",
    "floor_cleanliness",
    "raw_and_cooked_cross_contact_risk",
]


class HygieneIndicatorObservation(BaseModel):
    status: HygieneIndicatorStatus
    evidence: str = Field(max_length=300)


class HygieneFrameObservations(BaseModel):
    people_visible: int = Field(ge=0, le=100)
    gloves_in_use: HygieneIndicatorObservation
    hair_covering: HygieneIndicatorObservation
    apron_or_clean_uniform: HygieneIndicatorObservation
    hand_to_face_or_hair_contact: HygieneIndicatorObservation
    personal_phone_use: HygieneIndicatorObservation
    food_contact_with_bare_hands: HygieneIndicatorObservation
    food_on_floor_or_unsafe_storage: HygieneIndicatorObservation
    surface_cleanliness: HygieneIndicatorObservation
    floor_cleanliness: HygieneIndicatorObservation
    raw_and_cooked_cross_contact_risk: HygieneIndicatorObservation


class HygieneFrameSkipped(BaseModel):
    timestamp_seconds: float = Field(ge=0, allow_inf_nan=False)
    reason: str


class HygieneFrameFailed(BaseModel):
    timestamp_seconds: float = Field(ge=0, allow_inf_nan=False)
    reason: str


class HygieneViolation(BaseModel):
    indicator: HygieneIndicatorName
    severity: Literal["High", "Medium", "Low"]
    status: Literal["confirmed", "possible"]
    timestamps_seconds: list[
        Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ] = Field(default_factory=list)
    frame_count: int = Field(ge=1)
    evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    suggested_action: str


class HygieneAlert(BaseModel):
    level: Literal["info", "warning", "critical"]
    title: str
    message: str


class HygieneCategoryScores(BaseModel):
    protective_equipment: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    food_handling: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    cleanliness: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )


class HygieneCategoryEvidenceCoverage(BaseModel):
    protective_equipment: float = Field(ge=0, le=1, allow_inf_nan=False)
    food_handling: float = Field(ge=0, le=1, allow_inf_nan=False)
    cleanliness: float = Field(ge=0, le=1, allow_inf_nan=False)


class HygieneAnalysisResponse(BaseModel):
    success: bool
    overall_score: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    status: Literal[
        "good",
        "needs_attention",
        "action_required",
        "insufficient_evidence",
    ]
    category_scores: HygieneCategoryScores
    evidence_coverage: float = Field(ge=0, le=1, allow_inf_nan=False)
    category_evidence_coverage: HygieneCategoryEvidenceCoverage
    violations: list[HygieneViolation] = Field(default_factory=list)
    alerts: list[HygieneAlert] = Field(default_factory=list)
    summary: str
    frames_analyzed: int = Field(ge=0)
    frames_skipped: list[HygieneFrameSkipped] = Field(default_factory=list)
    frames_failed: list[HygieneFrameFailed] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)


RecipeInputType = Literal["image", "text", "image_and_text"]
RecipeStatus = Literal["ok", "needs_clarification"]
RecipeSkillLevel = Literal["beginner", "intermediate", "advanced"]
RecipeActionType = Literal[
    "prep",
    "chop",
    "heat",
    "mix",
    "cook",
    "rest",
    "serve",
    "other",
]
RecipeHeatLevel = Literal["low", "medium", "high"]


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=250)
    from_input: bool
    dietary_conflict: bool = False


class RecipeStep(BaseModel):
    step_number: int = Field(ge=1, le=100)
    instruction: str = Field(min_length=1, max_length=500)
    action_type: RecipeActionType
    duration_minutes: float | None = Field(
        default=None,
        ge=0,
        le=1440,
        allow_inf_nan=False,
    )
    heat_level: RecipeHeatLevel | None = None
    tip: str | None = Field(default=None, max_length=300)


class RecipeModelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RecipeStatus
    interpreted_goal: str = Field(min_length=1, max_length=300)
    clarifying_question: str | None = Field(default=None, max_length=300)
    dish_name: str | None = Field(default=None, max_length=150)
    cuisine: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    ingredients: list[RecipeIngredient] = Field(default_factory=list, max_length=50)
    steps: list[RecipeStep] = Field(default_factory=list, max_length=50)
    prep_time_minutes: float | None = Field(default=None, ge=0, le=1440, allow_inf_nan=False)
    cook_time_minutes: float | None = Field(default=None, ge=0, le=1440, allow_inf_nan=False)
    difficulty: RecipeSkillLevel | None = None
    equipment: list[str] = Field(default_factory=list, max_length=30)
    safety_notes: list[str] = Field(default_factory=list, max_length=30)
    substitutions: list[str] = Field(default_factory=list, max_length=30)
    uncertainties: list[str] = Field(default_factory=list, max_length=30)

class RecipeAllergens(BaseModel):
    contains: list[
        Literal[
            "milk",
            "egg",
            "peanut",
            "tree nuts",
            "wheat/gluten",
            "soy",
            "fish",
            "shellfish",
            "sesame",
        ]
    ] = Field(default_factory=list)


class RecipeGenerationResponse(BaseModel):
    success: bool
    status: RecipeStatus
    input_type: RecipeInputType
    interpreted_goal: str
    clarifying_question: str | None = None
    dish_name: str | None = None
    cuisine: str | None = None
    description: str | None = None
    servings: int = Field(ge=1, le=12)
    skill_level: RecipeSkillLevel
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    prep_time_minutes: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cook_time_minutes: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    total_time_minutes: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    difficulty: RecipeSkillLevel | None = None
    equipment: list[str] = Field(default_factory=list)
    allergens: RecipeAllergens
    safety_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)


ProfileSex = Literal["female", "male", "other", "prefer_not_to_say"]
ProfileHeightUnit = Literal["cm", "in"]
ProfileWeightUnit = Literal["kg", "lb"]
ProfileActivityLevel = Literal[
    "sedentary", "light", "moderate", "active", "very_active"
]
ProfileHealthGoal = Literal[
    "maintain", "lose_weight", "gain_weight", "build_muscle", "eat_healthier"
]
ProfileDietType = Literal[
    "omnivore",
    "vegetarian",
    "vegan",
    "pescatarian",
    "eggetarian",
    "jain",
    "halal",
    "kosher",
    "other",
]
CanonicalAllergen = Literal[
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
]
ExclusionReason = Literal["allergy", "diet", "restriction", "dislike"]
SafetyFlagSeverity = Literal["info", "warning", "consult_professional"]


class UserProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_years: int = Field(ge=13, le=100)
    sex: ProfileSex
    height: float = Field(gt=0, allow_inf_nan=False)
    height_unit: ProfileHeightUnit
    weight: float = Field(gt=0, allow_inf_nan=False)
    weight_unit: ProfileWeightUnit
    activity_level: ProfileActivityLevel
    health_goal: ProfileHealthGoal
    diet_type: ProfileDietType
    allergies: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=20
    )
    food_restrictions: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=20
    )
    dislikes: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=20
    )
    medical_conditions: list[Annotated[str, Field(min_length=1, max_length=500)]] | None = Field(
        default=None, max_length=10
    )
    pregnant_or_breastfeeding: bool | None = None
    meals_per_day: int = Field(default=3, ge=2, le=6)
    cuisine_preferences: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=10
    )

    @field_validator(
        "sex",
        "height_unit",
        "weight_unit",
        "activity_level",
        "health_goal",
        "diet_type",
        mode="before",
    )
    @classmethod
    def clean_categories(cls, value: object) -> object:
        return _clean_profile_text(value)

    @field_validator(
        "allergies",
        "food_restrictions",
        "dislikes",
        "medical_conditions",
        "cuisine_preferences",
        mode="before",
    )
    @classmethod
    def clean_text_lists(cls, value: object) -> object:
        if value is None or not isinstance(value, list):
            return value
        return [_clean_profile_text(item) for item in value]


def _clean_profile_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in cleaned):
        raise ValueError("Control characters are not allowed.")
    return cleaned


class ExcludedFood(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    reason: ExclusionReason
    strict: bool


class ProfileSafetyFlag(BaseModel):
    code: str
    message: str
    severity: SafetyFlagSeverity


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    created_at: datetime
    age_years: int = Field(ge=13, le=100)
    sex: ProfileSex
    height: float = Field(gt=0, allow_inf_nan=False)
    height_unit: ProfileHeightUnit
    weight: float = Field(gt=0, allow_inf_nan=False)
    weight_unit: ProfileWeightUnit
    height_cm: float = Field(ge=100, le=250, allow_inf_nan=False)
    weight_kg: float = Field(ge=25, le=300, allow_inf_nan=False)
    bmi: float = Field(gt=0, allow_inf_nan=False)
    activity_level: ProfileActivityLevel
    health_goal: ProfileHealthGoal
    diet_type: ProfileDietType
    meals_per_day: int = Field(ge=2, le=6)
    cuisine_preferences: list[str] = Field(default_factory=list, max_length=10)
    food_restrictions: list[str] = Field(default_factory=list, max_length=20)
    dislikes: list[str] = Field(default_factory=list, max_length=20)
    allergens: list[CanonicalAllergen] = Field(default_factory=list, max_length=20)
    unrecognized_allergies: list[str] = Field(default_factory=list, max_length=20)
    excluded_foods: list[ExcludedFood] = Field(default_factory=list, max_length=100)
    medical_conditions: list[str] = Field(default_factory=list, max_length=10)
    pregnant_or_breastfeeding: bool | None = None
    safety_flags: list[ProfileSafetyFlag] = Field(default_factory=list)
    requires_professional_review: bool
    warnings: list[str] = Field(default_factory=list)
    completeness_score: float = Field(ge=0, le=100, allow_inf_nan=False)
    schema_version: str = "1.0"


class UserProfileOptions(BaseModel):
    sexes: list[ProfileSex]
    activity_levels: list[ProfileActivityLevel]
    health_goals: list[ProfileHealthGoal]
    diet_types: list[ProfileDietType]
    canonical_allergens: list[CanonicalAllergen]
    height_units: list[ProfileHeightUnit]
    weight_units: list[ProfileWeightUnit]


MealPlanType = Literal["daily", "weekly"]
MealPlanStatus = Literal["ok", "professional_review_required", "partial"]
MealPlanBudget = Literal["low", "medium", "high"]
MealPlanAlertLevel = Literal["none", "info", "warning", "critical"]
MealNutritionSource = Literal["model_estimate", "computed"]


class MealPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    plan_type: MealPlanType = "daily"
    days: int = Field(default=7, ge=1, le=7)
    meals_per_day: int | None = Field(default=None, ge=2, le=6)
    budget_level: MealPlanBudget | None = None
    cooking_time_minutes_max: int | None = Field(default=None, ge=5, le=120)
    recent_history: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=14
    )
    weight_change_kg_per_week: float | None = Field(
        default=None, ge=-2, le=2, allow_inf_nan=False
    )
    acknowledge_review: bool = False

    @field_validator("recent_history", mode="before")
    @classmethod
    def clean_history(cls, value: object) -> object:
        if value is None or not isinstance(value, list):
            return value
        return [_clean_profile_text(item) for item in value]


class NutritionTargets(BaseModel):
    calories: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    protein_g: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    carbs_g: float | None = Field(default=None, ge=0, le=2000, allow_inf_nan=False)
    fats_g: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    fiber_g: float | None = Field(default=None, ge=0, le=500, allow_inf_nan=False)
    hydration_ml: int | None = Field(default=None, ge=0, le=20000)
    notes: list[str] = Field(default_factory=list, max_length=20)


class MealNutrition(BaseModel):
    calories_kcal: float = Field(ge=0, le=10000, allow_inf_nan=False)
    protein_g: float = Field(ge=0, le=1000, allow_inf_nan=False)
    carbs_g: float = Field(ge=0, le=2000, allow_inf_nan=False)
    fats_g: float = Field(ge=0, le=1000, allow_inf_nan=False)
    fiber_g: float = Field(ge=0, le=500, allow_inf_nan=False)


class DailyNutritionTotals(BaseModel):
    calories_kcal: float = Field(ge=0, le=60000, allow_inf_nan=False)
    protein_g: float = Field(ge=0, le=6000, allow_inf_nan=False)
    carbs_g: float = Field(ge=0, le=12000, allow_inf_nan=False)
    fats_g: float = Field(ge=0, le=6000, allow_inf_nan=False)
    fiber_g: float = Field(ge=0, le=3000, allow_inf_nan=False)


class MealIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity_g: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    notes: str | None = Field(default=None, max_length=250)


class MealCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dish_name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=400)
    ingredients: list[MealIngredient] = Field(min_length=1, max_length=40)
    portion_size: str = Field(min_length=1, max_length=100)
    prep_style: str = Field(min_length=1, max_length=100)
    prep_time_minutes: int = Field(ge=0, le=1440)
    estimated_nutrition: MealNutrition


class MealModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_slot: str = Field(min_length=1, max_length=40)
    meal: MealCandidate
    alternatives: list[MealCandidate] = Field(min_length=2, max_length=2)


class MealDayModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meals: list[MealModelOutput] = Field(min_length=1, max_length=6)


class PlannedMeal(BaseModel):
    meal_slot: str = Field(min_length=1, max_length=40)
    status: Literal["available", "unavailable"]
    dish_name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=400)
    ingredients: list[MealIngredient] = Field(default_factory=list, max_length=40)
    portion_size: str | None = Field(default=None, max_length=100)
    prep_style: str | None = Field(default=None, max_length=100)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=1440)
    estimated_nutrition: MealNutrition | None = None
    nutrition_source: MealNutritionSource | None = None
    nutrition_notes: list[str] = Field(default_factory=list, max_length=10)
    alternatives: list[MealCandidate] = Field(default_factory=list, max_length=2)
    unavailable_reason: str | None = Field(default=None, max_length=300)


class MealTargetDifference(BaseModel):
    calories_percent: float = Field(ge=-100, le=10000, allow_inf_nan=False)
    protein_percent: float = Field(ge=-100, le=10000, allow_inf_nan=False)
    carbs_percent: float = Field(ge=-100, le=10000, allow_inf_nan=False)
    fats_percent: float = Field(ge=-100, le=10000, allow_inf_nan=False)
    fiber_percent: float = Field(ge=-100, le=20000, allow_inf_nan=False)


class DailyMealPlan(BaseModel):
    day_number: int = Field(ge=1, le=7)
    meals: list[PlannedMeal] = Field(max_length=6)
    daily_totals: DailyNutritionTotals
    target_difference_percent: MealTargetDifference


class FailedPlanDay(BaseModel):
    day_number: int = Field(ge=1, le=7)
    reason: Literal[
        "rate limited",
        "timed out",
        "service unavailable",
        "invalid model response",
        "service not configured",
    ]


class MealMacroBalance(BaseModel):
    carbs: float = Field(ge=0, le=100, allow_inf_nan=False)
    protein: float = Field(ge=0, le=100, allow_inf_nan=False)
    fat: float = Field(ge=0, le=100, allow_inf_nan=False)


class WeeklyMealReport(BaseModel):
    average_daily_calories: float | None = Field(
        default=None, ge=0, le=10000, allow_inf_nan=False
    )
    average_calories_difference_percent: float | None = Field(
        default=None, allow_inf_nan=False
    )
    average_macro_balance: MealMacroBalance = Field(
        default_factory=lambda: MealMacroBalance(carbs=0, protein=0, fat=0)
    )
    variety_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    days_within_10_percent_of_target: int = Field(ge=0, le=7)
    concern_areas: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class MealPlanResponse(BaseModel):
    success: bool
    status: MealPlanStatus
    plan_type: MealPlanType
    targets: NutritionTargets
    days: list[DailyMealPlan] = Field(default_factory=list, max_length=7)
    weekly_report: WeeklyMealReport | None = None
    general_outline_type: Literal["general_healthy_eating"] | None = None
    general_outline: list[str] = Field(default_factory=list, max_length=10)
    adaptive_suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failed_days: list[FailedPlanDay] = Field(default_factory=list, max_length=7)
    safety_flags: list[ProfileSafetyFlag] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)
    alert_level: MealPlanAlertLevel
