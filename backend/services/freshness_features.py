from __future__ import annotations

import cv2
import numpy as np

from backend.schemas import (
    ColorFeatures,
    DominantColor,
    FreshnessFeatures,
    QualityFlags,
    SurfacePatternFeatures,
    TextureFeatures,
)
from backend.services.image_processing import InvalidImageError, preprocess_image

FEATURE_VERSION = "1.0"
KMEANS_CLUSTERS = 3

# OpenCV HSV hue is [0, 179], saturation/value are [0, 255].
DARK_HSV_LOWER = np.array([0, 0, 0], dtype=np.uint8)
DARK_HSV_UPPER = np.array([179, 255, 55], dtype=np.uint8)
BROWN_HSV_LOWER = np.array([5, 45, 20], dtype=np.uint8)
BROWN_HSV_UPPER = np.array([25, 255, 190], dtype=np.uint8)
YELLOW_HSV_LOWER = np.array([20, 45, 80], dtype=np.uint8)
YELLOW_HSV_UPPER = np.array([40, 255, 255], dtype=np.uint8)
MOLD_LIKE_HSV_RANGES = (
    (np.array([0, 0, 80], dtype=np.uint8), np.array([179, 70, 255], dtype=np.uint8)),
    (np.array([35, 20, 25], dtype=np.uint8), np.array([100, 255, 200], dtype=np.uint8)),
)


def _decode_normalized_image(
    image_bytes: bytes,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    processed_bytes = preprocess_image(image_bytes)
    encoded = np.frombuffer(processed_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise InvalidImageError("Image data could not be decoded safely.")

    denoised = cv2.fastNlMeansDenoisingColored(
        image_bgr,
        None,
        h=5,
        hColor=5,
        templateWindowSize=7,
        searchWindowSize=21,
    )
    original_hsv = cv2.cvtColor(denoised, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    normalized_lab = cv2.merge((clahe.apply(lightness), a_channel, b_channel))
    normalized_bgr = cv2.cvtColor(normalized_lab, cv2.COLOR_LAB2BGR)
    normalized_hsv = cv2.cvtColor(normalized_bgr, cv2.COLOR_BGR2HSV)
    return normalized_bgr, normalized_hsv, original_hsv


def _dominant_colors(image_bgr: np.ndarray) -> list[DominantColor]:
    pixels = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).reshape(-1, 3)
    pixels = pixels.astype(np.float32)
    if pixels.shape[0] < KMEANS_CLUSTERS:
        pixels = np.resize(pixels, (KMEANS_CLUSTERS, 3))
    cv2.setRNGSeed(0)
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        20,
        1.0,
    )
    _compactness, labels, centers = cv2.kmeans(
        pixels,
        KMEANS_CLUSTERS,
        None,
        criteria,
        1,
        cv2.KMEANS_PP_CENTERS,
    )
    counts = np.bincount(labels.flatten(), minlength=KMEANS_CLUSTERS)
    order = np.argsort(counts)[::-1]
    total = float(counts.sum())
    return [
        DominantColor(
            red=float(np.clip(centers[index, 0], 0, 255)),
            green=float(np.clip(centers[index, 1], 0, 255)),
            blue=float(np.clip(centers[index, 2], 0, 255)),
            percentage=float(counts[index] / total * 100),
        )
        for index in order
    ]


def _color_consistency(hsv: np.ndarray) -> float:
    hue = hsv[:, :, 0].astype(np.float32)
    saturation = hsv[:, :, 1].astype(np.float32)
    hue_spread = min(float(np.std(hue)) / 90.0, 1.0)
    saturation_spread = min(float(np.std(saturation)) / 127.5, 1.0)
    return float(np.clip(1.0 - (hue_spread + saturation_spread) / 2.0, 0, 1))


def _fraction(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask) / mask.size)


def _local_standard_deviation(gray: np.ndarray) -> np.ndarray:
    gray_float = gray.astype(np.float32)
    mean = cv2.blur(gray_float, (7, 7))
    mean_square = cv2.blur(gray_float * gray_float, (7, 7))
    return np.sqrt(np.maximum(mean_square - mean * mean, 0))


def _mold_like_fraction(hsv: np.ndarray) -> float:
    candidate_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in MOLD_LIKE_HSV_RANGES:
        candidate_mask = cv2.bitwise_or(
            candidate_mask,
            cv2.inRange(hsv, lower, upper),
        )

    contours, _hierarchy = cv2.findContours(
        candidate_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    total_area = float(hsv.shape[0] * hsv.shape[1])
    max_blob_area = total_area * 0.05
    mold_area = 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if area <= 1 or area > max_blob_area or perimeter <= 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.9:
            mold_area += area
    return float(np.clip(mold_area / total_area, 0, 1))


def extract_freshness_features(image_bytes: bytes) -> FreshnessFeatures:
    """Measure visual image features; this function does not classify freshness."""
    image_bgr, hsv, original_hsv = _decode_normalized_image(image_bytes)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    local_std = _local_standard_deviation(gray)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    local_std_mean = float(local_std.mean())
    smoothness = float(np.clip(1.0 - local_std_mean / 127.5, 0, 1))
    gray_contrast = float(np.std(gray))
    mean_value = float(np.mean(original_hsv[:, :, 2]))

    dark_mask = cv2.inRange(hsv, DARK_HSV_LOWER, DARK_HSV_UPPER)
    brown_mask = cv2.inRange(hsv, BROWN_HSV_LOWER, BROWN_HSV_UPPER)
    yellow_mask = cv2.inRange(hsv, YELLOW_HSV_LOWER, YELLOW_HSV_UPPER)
    discoloration = cv2.bitwise_or(brown_mask, yellow_mask)
    edges = cv2.Canny(gray, 100, 200)

    features = FreshnessFeatures(
        feature_version=FEATURE_VERSION,
        color=ColorFeatures(
            mean_h=float(np.mean(hsv[:, :, 0])),
            std_h=float(np.std(hsv[:, :, 0])),
            mean_s=float(np.mean(hsv[:, :, 1])),
            std_s=float(np.std(hsv[:, :, 1])),
            mean_v=mean_value,
            std_v=float(np.std(hsv[:, :, 2])),
            dominant_colors=_dominant_colors(image_bgr),
            consistency_score=_color_consistency(hsv),
        ),
        dark_discoloration_fraction=_fraction(dark_mask),
        yellow_brown_fraction=_fraction(discoloration),
        texture=TextureFeatures(
            laplacian_variance=laplacian_variance,
            local_standard_deviation=local_std_mean,
            smoothness_score=smoothness,
        ),
        surface_patterns=SurfacePatternFeatures(
            edge_density=_fraction(edges),
            mold_like_pattern_fraction=_mold_like_fraction(hsv),
        ),
        quality_flags=QualityFlags(
            too_dark=mean_value < 50,
            too_bright=mean_value > 220,
            blurry=laplacian_variance < 20,
            low_contrast=gray_contrast < 15,
        ),
        warnings=[
            "Color and surface-pattern thresholds are image-level visual heuristics."
        ],
    )
    problems = validate_features(features)
    if problems:
        raise ValueError("Extracted freshness features failed validation: " + "; ".join(problems))
    return features


def validate_features(features: FreshnessFeatures) -> list[str]:
    """Return non-finite or out-of-range feature values with their field paths."""
    problems = []
    values = features.model_dump()
    numeric_ranges = {
        "color.mean_h": (0, 179),
        "color.std_h": (0, 90),
        "color.mean_s": (0, 255),
        "color.std_s": (0, 127.5),
        "color.mean_v": (0, 255),
        "color.std_v": (0, 127.5),
        "color.consistency_score": (0, 1),
        "dark_discoloration_fraction": (0, 1),
        "yellow_brown_fraction": (0, 1),
        "texture.laplacian_variance": (0, 1_000_000_000),
        "texture.local_standard_deviation": (0, 127.5),
        "texture.smoothness_score": (0, 1),
        "surface_patterns.edge_density": (0, 1),
        "surface_patterns.mold_like_pattern_fraction": (0, 1),
    }
    for index, _color in enumerate(values["color"]["dominant_colors"]):
        for channel in ("red", "green", "blue"):
            numeric_ranges[f"color.dominant_colors.{index}.{channel}"] = (0, 255)
        numeric_ranges[f"color.dominant_colors.{index}.percentage"] = (0, 100)

    for field_path, (minimum, maximum) in numeric_ranges.items():
        value: object = values
        for part in field_path.split("."):
            value = value[int(part)] if part.isdigit() else value[part]
        if not isinstance(value, (int, float)) or not np.isfinite(value):
            problems.append(f"{field_path} must be a finite number.")
        elif value < minimum or value > maximum:
            problems.append(
                f"{field_path}={value} is outside the documented range "
                f"[{minimum}, {maximum}]."
            )

    percentage_total = sum(
        color["percentage"] for color in values["color"]["dominant_colors"]
    )
    if not np.isfinite(percentage_total) or not np.isclose(percentage_total, 100, atol=1):
        problems.append("color.dominant_colors percentages must sum to 100 (+/- 1).")
    return problems
