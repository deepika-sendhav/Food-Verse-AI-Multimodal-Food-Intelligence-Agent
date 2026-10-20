import base64
import json
import os
from typing import Literal

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.config import GROQ_TIMEOUT_SECONDS, GROQ_VISION_MODEL
from backend.schemas import FreshnessFeatures


class ModelTimeoutError(Exception):
    pass


class ModelUnavailableError(Exception):
    pass


class ModelResponseError(Exception):
    pass


class FreshnessModelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_name: str | None = Field(default=None, max_length=100)
    freshness_level: Literal[
        "fresh",
        "moderately_fresh",
        "spoiled",
        "uncertain",
    ]
    detected_signs: list[str] = Field(default_factory=list, max_length=20)
    reasoning: str = Field(min_length=1, max_length=500)


async def classify_freshness(
    image_bytes: bytes,
    features: FreshnessFeatures,
    storage_time: str | None = None,
    storage_type: str | None = None,
) -> FreshnessModelResult:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ModelUnavailableError("GROQ_API_KEY is not configured.")

    prompt = (
        "Assess the freshness of the food visible in this image. Judge only what is "
        "visible. Do not claim certainty from one photo. Natural ripening is not "
        "spoilage: brown spots on a banana, a slightly wrinkled peel, or dark natural "
        "colors (chocolate, dark curry, cooked spinach) are not mold. Mold means fuzzy "
        "or powdery white, green, blue or black growth; spoilage also includes slime, "
        "liquid pooling, collapsed or mushy texture, and visible rot. If the image is "
        "unclear, too dark, blurry, or shows no food, return freshness_level "
        "\"uncertain\". Use the measured features as supporting evidence only. If the "
        "features and the image disagree, say so in reasoning. Do not infer unseen "
        "storage conditions or hidden ingredients. Return JSON with exactly these "
        "fields: item_name (string or null), freshness_level (one of fresh, "
        "moderately_fresh, spoiled, uncertain), detected_signs (array of short strings), "
        "reasoning (short string). Do not return any confidence number.\n\n"
        f"Measured visual features: {json.dumps(features.model_dump(), separators=(',', ':'))}\n"
        f"Reported storage time: {storage_time or 'not provided'}\n"
        f"Reported storage type: {storage_type or 'not provided'}"
    )
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    try:
        async with AsyncGroq(
            api_key=api_key,
            timeout=GROQ_TIMEOUT_SECONDS,
            max_retries=0,
        ) as client:
            completion = await client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=500,
            )
    except APITimeoutError as exc:
        raise ModelTimeoutError from exc
    except (APIConnectionError, RateLimitError, APIStatusError) as exc:
        raise ModelUnavailableError from exc

    try:
        message = completion.choices[0].message.content
        if not isinstance(message, str) or not message.strip():
            raise ValueError("The model response was empty.")
        parsed = json.loads(message)
        return FreshnessModelResult.model_validate(parsed)
    except (IndexError, AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise ModelResponseError from exc
