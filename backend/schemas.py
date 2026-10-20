from typing import Annotated, Literal

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
