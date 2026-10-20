from typing import Literal

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
