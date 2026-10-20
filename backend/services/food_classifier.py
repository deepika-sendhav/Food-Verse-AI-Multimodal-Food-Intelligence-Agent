import base64
import json
import os

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
)
from pydantic import ValidationError

from backend.config import GROQ_TIMEOUT_SECONDS, GROQ_VISION_MODEL
from backend.schemas import FoodModelResult


class ModelTimeoutError(Exception):
    pass


class ModelUnavailableError(Exception):
    pass


class ModelResponseError(Exception):
    pass


async def classify_food(image_bytes: bytes) -> FoodModelResult:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ModelUnavailableError("GROQ_API_KEY is not configured.")

    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "Analyze this food image. Identify the most likely dish and clearly visible edible "
        "food or drink items only. Use simple, consistent names for items (for example "
        "\"green chili\", not \"stuffed pepper\" or \"stuffed green chili\"). List side "
        "garnishes such as chili, lime, onion, and cilantro as separate items. Each "
        "detected_items entry must be a short common food name; do not include descriptive "
        "phrases or serving containers. The detected_items array must contain only edible "
        "foods, ingredients, or drinks. Never include utensils, plates, bowls, cups, glasses, "
        "trays, containers, packaging, tableware, furniture, or any other non-food object in "
        "detected_items. Do not infer hidden ingredients or claim certainty when the image is "
        "unclear. If the image shows a single food item, set dish_name to that item's simple "
        "name (for example, \"banana\") instead of null. If there is not enough visual "
        "evidence to name a dish, use null for dish_name, list only edible items that are "
        "identifiable (or an empty array), and explain uncertainty. Return JSON with exactly "
        "these fields: dish_name (string or "
        "null), detected_items (array of edible food/drink strings only), description (short "
        "string), uncertainties (array of strings). Do not include a confidence score."
    )

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
        return FoodModelResult.model_validate(parsed)
    except (IndexError, AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise ModelResponseError from exc
