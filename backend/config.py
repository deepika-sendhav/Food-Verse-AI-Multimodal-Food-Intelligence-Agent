import math
import os

from dotenv import load_dotenv

load_dotenv()


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive number.") from exc
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"{name} must be a positive number.")
    return value


GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "").strip() or "qwen/qwen3.8-27b"
GROQ_TIMEOUT_SECONDS = _positive_float("GROQ_TIMEOUT_SECONDS", 30.0)
MAX_UPLOAD_SIZE_BYTES = _positive_int("FOOD_IMAGE_MAX_BYTES", 10 * 1024 * 1024)
MAX_IMAGE_SIDE = _positive_int("FOOD_IMAGE_MAX_SIDE", 2048)
USDA_FDC_API_KEY = os.getenv("USDA_FDC_API_KEY", "").strip()
DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().casefold() in {
    "1",
    "true",
    "yes",
    "on",
}
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
)
if "*" in CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS must not contain a wildcard.")
HYGIENE_VIDEO_MAX_BYTES = _positive_int("HYGIENE_VIDEO_MAX_BYTES", 50 * 1024 * 1024)
HYGIENE_VIDEO_MAX_SECONDS = _positive_float("HYGIENE_VIDEO_MAX_SECONDS", 120.0)
HYGIENE_MAX_FRAMES = _positive_int("HYGIENE_MAX_FRAMES", 12)
HYGIENE_MAX_CONCURRENCY = _positive_int("HYGIENE_MAX_CONCURRENCY", 1)
HYGIENE_FRAME_DELAY_SECONDS = _positive_float(
    "HYGIENE_FRAME_DELAY_SECONDS",
    2.0,
)
HYGIENE_FRAME_MAX_SIDE = _positive_int("HYGIENE_FRAME_MAX_SIDE", 768)
PROFILE_TTL_MINUTES = _positive_int("PROFILE_TTL_MINUTES", 60)
