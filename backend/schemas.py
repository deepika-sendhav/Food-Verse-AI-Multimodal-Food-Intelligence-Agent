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
