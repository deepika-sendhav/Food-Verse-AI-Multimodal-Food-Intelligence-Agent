import asyncio
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.config import DEMO_MODE, MAX_UPLOAD_SIZE_BYTES
from backend.schemas import RecipeGenerationResponse
from backend.services.image_processing import InvalidImageError, preprocess_image
from backend.services.recipe_generator import (
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRateLimitedError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    build_recipe_response,
    generate_recipe,
)
from backend.services.demo_responses import load_demo_response

router = APIRouter(prefix="/api/kitchen", tags=["kitchen assistant"])

ALLOWED_UPLOADS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.post("/generate-recipe", response_model=RecipeGenerationResponse)
async def generate_recipe_endpoint(
    text_input: str | None = Form(default=None, max_length=1000),
    file: UploadFile | None = File(default=None),
    servings: int = Form(default=2, ge=1, le=12),
    skill_level: Literal["beginner", "intermediate", "advanced"] = Form(
        default="beginner"
    ),
    dietary_preferences: str | None = Form(default=None, max_length=200),
) -> RecipeGenerationResponse | JSONResponse:
    cleaned_text = text_input.strip() if text_input else None
    cleaned_preferences = (
        dietary_preferences.strip() if dietary_preferences else None
    )
    if cleaned_text == "":
        cleaned_text = None
    if cleaned_preferences == "":
        cleaned_preferences = None
    if cleaned_text is None and file is None:
        raise HTTPException(
            status_code=422,
            detail="Provide text_input, an image file, or both to generate a recipe.",
        )

    try:
        processed_image = None
        if file is not None:
            suffix = ""
            if file.filename and "." in file.filename:
                suffix = f".{file.filename.rsplit('.', 1)[-1].lower()}"
            expected_type = ALLOWED_UPLOADS.get(suffix)
            content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
            if expected_type is None or content_type != expected_type:
                raise HTTPException(
                    status_code=415,
                    detail="Upload a JPG, PNG, or WEBP image with a matching image MIME type.",
                )

            image_bytes = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
            if not image_bytes:
                raise HTTPException(status_code=400, detail="The uploaded image is empty.")
            if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="The uploaded image exceeds the size limit.",
                )
            try:
                processed_image = await asyncio.to_thread(preprocess_image, image_bytes)
            except InvalidImageError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="The upload is not a valid, supported image.",
                ) from exc

        input_type = (
            "image_and_text"
            if processed_image is not None and cleaned_text is not None
            else "image"
            if processed_image is not None
            else "text"
        )
        if DEMO_MODE:
            return load_demo_response(
                "kitchen_assistant",
                RecipeGenerationResponse,
            )
        try:
            model_result = await generate_recipe(
                text_input=cleaned_text,
                image_bytes=processed_image,
                servings=servings,
                skill_level=skill_level,
                dietary_preferences=cleaned_preferences,
            )
        except ModelTimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="The recipe service timed out. Please try again.",
            ) from exc
        except ModelUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail="The recipe service is unavailable or not configured.",
            ) from exc
        except ModelNotConfiguredError as exc:
            raise HTTPException(
                status_code=503,
                detail="The recipe service is not configured.",
            ) from exc
        except ModelConnectionError as exc:
            raise HTTPException(
                status_code=503,
                detail="The recipe service is unreachable.",
            ) from exc
        except ModelRateLimitedError as exc:
            headers = (
                {"Retry-After": exc.retry_after}
                if exc.retry_after is not None
                else None
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "The recipe service is rate limited; please try again in a minute"
                },
                headers=headers,
            )
        except ModelResponseError as exc:
            raise HTTPException(
                status_code=502,
                detail="The recipe service returned an invalid response.",
            ) from exc

        return build_recipe_response(
            model_result,
            input_type=input_type,
            servings=servings,
            skill_level=skill_level,
            dietary_preferences=cleaned_preferences,
        )
    finally:
        if file is not None:
            await file.close()
