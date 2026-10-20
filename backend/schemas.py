from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("detected_items", "uncertainties")
    @classmethod
    def clean_list_items(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in values if item.strip()))


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
