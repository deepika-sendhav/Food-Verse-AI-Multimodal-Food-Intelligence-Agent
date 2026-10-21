import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.config import (
    DEMO_MODE,
    HYGIENE_VIDEO_MAX_BYTES,
    HYGIENE_VIDEO_MAX_SECONDS,
    MAX_UPLOAD_SIZE_BYTES,
)
from backend.schemas import HygieneAnalysisResponse
from backend.services.hygiene_analyzer import analyze_frames, build_hygiene_response
from backend.services.image_processing import InvalidImageError
from backend.services.video_frames import (
    VIDEO_SUFFIXES,
    InvalidVideoError,
    extract_media_frames,
)
from backend.services.demo_responses import load_demo_response

router = APIRouter(prefix="/api/hygiene", tags=["kitchen hygiene"])

ALLOWED_UPLOADS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
}


@router.post("/analyze", response_model=HygieneAnalysisResponse)
async def analyze_hygiene(
    file: UploadFile = File(...),
    context_rules: str | None = Form(default=None, max_length=500),
    interval_seconds: int = Form(default=5, ge=1, le=30),
) -> HygieneAnalysisResponse:
    try:
        suffix = ""
        if file.filename and "." in file.filename:
            suffix = f".{file.filename.rsplit('.', 1)[-1].lower()}"
        expected_content_type = ALLOWED_UPLOADS.get(suffix)
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if expected_content_type is None or expected_content_type != content_type:
            raise HTTPException(
                status_code=415,
                detail="Upload a supported image or MP4, MOV, AVI, or WEBM video with a matching MIME type.",
            )

        upload_limit = (
            HYGIENE_VIDEO_MAX_BYTES
            if suffix in VIDEO_SUFFIXES
            else MAX_UPLOAD_SIZE_BYTES
        )
        media_bytes = await file.read(upload_limit + 1)
        if not media_bytes:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        if len(media_bytes) > upload_limit:
            raise HTTPException(status_code=413, detail="The uploaded file exceeds the size limit.")

        if DEMO_MODE:
            return load_demo_response("hygiene", HygieneAnalysisResponse)

        try:
            extracted = await asyncio.to_thread(
                extract_media_frames,
                media_bytes,
                suffix,
                interval_seconds,
                max_video_seconds=HYGIENE_VIDEO_MAX_SECONDS,
            )
        except InvalidImageError as exc:
            raise HTTPException(
                status_code=422,
                detail="The uploaded image is not valid or supported.",
            ) from exc
        except InvalidVideoError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        analyzed, failed = await analyze_frames(extracted.frames, context_rules)
        if extracted.frames and not analyzed:
            raise HTTPException(
                status_code=503,
                detail="The vision service could not analyze any selected frames.",
            )
        return build_hygiene_response(analyzed, extracted.skipped, failed)
    finally:
        await file.close()
