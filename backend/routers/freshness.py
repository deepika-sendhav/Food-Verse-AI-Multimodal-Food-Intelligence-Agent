from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import MAX_UPLOAD_SIZE_BYTES
from backend.schemas import FreshnessFeatures
from backend.services.freshness_features import extract_freshness_features
from backend.services.image_processing import InvalidImageError

router = APIRouter(prefix="/api/freshness", tags=["freshness features"])

ALLOWED_UPLOADS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.post("/features", response_model=FreshnessFeatures)
async def extract_image_features(file: UploadFile = File(...)) -> FreshnessFeatures:
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
            return extract_freshness_features(image_bytes)
        except InvalidImageError as exc:
            raise HTTPException(
                status_code=422,
                detail="The upload is not a valid, supported image.",
            ) from exc
    finally:
        await file.close()
