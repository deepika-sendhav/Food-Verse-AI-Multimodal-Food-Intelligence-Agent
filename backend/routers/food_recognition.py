import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import DEMO_MODE, MAX_UPLOAD_SIZE_BYTES
from backend.schemas import FoodAnalysisResponse
from backend.services.food_classifier import (
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    classify_food,
)
from backend.services.image_processing import InvalidImageError, preprocess_image
from backend.services.nutrition_estimation import estimate_nutrition
from backend.services.demo_responses import load_demo_response

router = APIRouter(prefix="/api/food-recognition", tags=["food recognition"])

ALLOWED_UPLOADS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.post("/analyze", response_model=FoodAnalysisResponse)
async def analyze_food_image(
    file: UploadFile = File(...),
    serving_size_g: float | None = Form(default=None, gt=0, le=5000),
) -> FoodAnalysisResponse:
    try:
        suffix = ""
        if file.filename:
            suffix = file.filename.rsplit(".", 1)[-1].lower()
            suffix = f".{suffix}" if "." in file.filename else ""
        expected_content_type = ALLOWED_UPLOADS.get(suffix)
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if expected_content_type is None or content_type != expected_content_type:
            raise HTTPException(
                status_code=415,
                detail="Upload a JPG, PNG, or WEBP image with a matching image MIME type.",
            )

        image_bytes = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
        if not image_bytes:
            raise HTTPException(status_code=400, detail="The uploaded image is empty.")
        if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="The uploaded image exceeds the size limit.")

        try:
            processed_image = await asyncio.to_thread(preprocess_image, image_bytes)
        except InvalidImageError as exc:
            raise HTTPException(
                status_code=422,
                detail="The upload is not a valid, supported image.",
            ) from exc

        if DEMO_MODE:
            return load_demo_response("food_recognition", FoodAnalysisResponse)

        try:
            result = await classify_food(processed_image)
        except ModelTimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="The food vision service timed out. Please try again.",
            ) from exc
        except ModelUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail="The food vision service is unavailable or not configured.",
            ) from exc
        except ModelResponseError as exc:
            raise HTTPException(
                status_code=502,
                detail="The food vision service returned an invalid response.",
            ) from exc

        (
            nutrition,
            health_score,
            health_label,
            reasoning,
            insights,
            alternatives,
        ) = await estimate_nutrition(
            dish_name=result.dish_name,
            detected_items=result.detected_items,
            serving_size_g=serving_size_g,
        )

        return FoodAnalysisResponse(
            success=True,
            dish_name=result.dish_name,
            detected_items=result.detected_items,
            confidence=None,
            description=result.description,
            uncertainties=list(dict.fromkeys(result.uncertainties + nutrition.uncertainties)),
            nutrition=nutrition,
            health_score=health_score,
            health_label=health_label,
            reasoning=reasoning,
            insights=insights,
            alternatives=alternatives,
        )
    finally:
        await file.close()
