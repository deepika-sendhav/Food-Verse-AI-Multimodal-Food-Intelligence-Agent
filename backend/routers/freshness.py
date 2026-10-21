import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import DEMO_MODE, MAX_UPLOAD_SIZE_BYTES
from backend.schemas import FreshnessAnalysisResponse, FreshnessFeatures
from backend.services.freshness_assessment import (
    assess_freshness_rules,
    combine_freshness_assessment,
)
from backend.services.freshness_classifier import (
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    classify_freshness,
)
from backend.services.freshness_features import extract_freshness_features
from backend.services.image_processing import InvalidImageError, preprocess_image
from backend.services.demo_responses import load_demo_payload, load_demo_response

router = APIRouter(prefix="/api/freshness", tags=["freshness features"])

ALLOWED_UPLOADS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


async def _read_upload(file: UploadFile) -> bytes:
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
    return image_bytes


def _invalid_image_error() -> HTTPException:
    return HTTPException(
        status_code=422,
        detail="The upload is not a valid, supported image.",
    )


@router.post("/features", response_model=FreshnessFeatures)
async def extract_image_features(file: UploadFile = File(...)) -> FreshnessFeatures:
    try:
        image_bytes = await _read_upload(file)
        if DEMO_MODE:
            return FreshnessFeatures.model_validate(
                load_demo_payload("freshness_features", FreshnessFeatures)
            )

        try:
            return await asyncio.to_thread(extract_freshness_features, image_bytes)
        except InvalidImageError as exc:
            raise _invalid_image_error() from exc
    finally:
        await file.close()


@router.post("/analyze", response_model=FreshnessAnalysisResponse)
async def analyze_freshness(
    file: UploadFile = File(...),
    storage_time: str | None = Form(default=None, max_length=100),
    storage_type: str | None = Form(default=None, max_length=100),
) -> FreshnessAnalysisResponse:
    try:
        image_bytes = await _read_upload(file)
        if DEMO_MODE:
            return load_demo_response("freshness", FreshnessAnalysisResponse)
        try:
            features, processed_image = await asyncio.gather(
                asyncio.to_thread(extract_freshness_features, image_bytes),
                asyncio.to_thread(preprocess_image, image_bytes),
            )
        except InvalidImageError as exc:
            raise _invalid_image_error() from exc

        rule_assessment = assess_freshness_rules(features)
        model_result = None
        model_skipped_reason = None
        try:
            model_result = await classify_freshness(
                processed_image,
                features,
                storage_time=storage_time,
                storage_type=storage_type,
            )
        except ModelTimeoutError:
            model_skipped_reason = "the vision service timed out."
        except ModelUnavailableError:
            model_skipped_reason = "the vision service is unavailable or not configured."
        except ModelResponseError:
            model_skipped_reason = "the vision service returned an invalid response."

        return combine_freshness_assessment(
            features,
            rule_assessment,
            model_result,
            storage_time=storage_time,
            storage_type=storage_type,
            model_skipped_reason=model_skipped_reason,
        )
    finally:
        await file.close()
