from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

import cv2
import numpy as np

from backend.config import (
    HYGIENE_MAX_FRAMES,
    HYGIENE_VIDEO_MAX_SECONDS,
)
from backend.services.image_processing import InvalidImageError, preprocess_image

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".webm"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
BLUR_LAPLACIAN_VARIANCE_MIN = 5.0
DARK_MEAN_BRIGHTNESS_MAX = 25.0
LOW_CONTRAST_STDDEV_MIN = 5.0
DUPLICATE_MEAN_PIXEL_DIFF_MAX = 3.0
DUPLICATE_HISTOGRAM_CORRELATION_MIN = 0.995


class InvalidVideoError(Exception):
    pass


@dataclass(frozen=True)
class SelectedFrame:
    timestamp_seconds: float
    image_bytes: bytes


@dataclass(frozen=True)
class SkippedFrame:
    timestamp_seconds: float
    reason: str


@dataclass(frozen=True)
class ExtractedFrames:
    frames: list[SelectedFrame]
    skipped: list[SkippedFrame]
    duration_seconds: float


def _jpeg_bytes(frame_bgr: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(
        ".jpg",
        frame_bgr,
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    )
    if not success:
        raise InvalidVideoError("A video frame could not be encoded.")
    try:
        return preprocess_image(encoded.tobytes())
    except InvalidImageError as exc:
        raise InvalidVideoError("A video frame could not be preprocessed.") from exc


def _skip_quality_reason(frame_bgr: np.ndarray) -> str | None:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if float(np.mean(gray)) < DARK_MEAN_BRIGHTNESS_MAX:
        return "frame skipped because it is too dark"
    if float(np.std(gray)) < LOW_CONTRAST_STDDEV_MIN:
        return "frame skipped because it has low contrast"
    if float(cv2.Laplacian(gray, cv2.CV_64F).var()) < BLUR_LAPLACIAN_VARIANCE_MIN:
        return "frame skipped because it is blurry"
    return None


def _near_duplicate(current: np.ndarray, previous: np.ndarray) -> bool:
    current_small = cv2.resize(current, (64, 64), interpolation=cv2.INTER_AREA)
    previous_small = cv2.resize(previous, (64, 64), interpolation=cv2.INTER_AREA)
    mean_difference = float(
        np.mean(
            cv2.absdiff(
                cv2.cvtColor(current_small, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(previous_small, cv2.COLOR_BGR2GRAY),
            )
        )
    )
    if mean_difference <= DUPLICATE_MEAN_PIXEL_DIFF_MAX:
        return True
    current_hist = cv2.calcHist([current_small], [0, 1], None, [16, 16], [0, 256, 0, 256])
    previous_hist = cv2.calcHist([previous_small], [0, 1], None, [16, 16], [0, 256, 0, 256])
    correlation = cv2.compareHist(current_hist, previous_hist, cv2.HISTCMP_CORREL)
    return (
        correlation >= DUPLICATE_HISTOGRAM_CORRELATION_MIN
        and mean_difference < 12.0
    )


def extract_media_frames(
    media_bytes: bytes,
    suffix: str,
    interval_seconds: int = 5,
    *,
    max_frames: int = HYGIENE_MAX_FRAMES,
    max_video_seconds: float = HYGIENE_VIDEO_MAX_SECONDS,
) -> ExtractedFrames:
    suffix = suffix.casefold()
    if not 1 <= interval_seconds <= 30:
        raise ValueError("interval_seconds must be between 1 and 30.")

    if suffix in IMAGE_SUFFIXES:
        try:
            processed = preprocess_image(media_bytes)
        except InvalidImageError:
            raise
        decoded = cv2.imdecode(np.frombuffer(processed, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise InvalidImageError("Image data could not be decoded safely.")
        reason = _skip_quality_reason(decoded)
        if reason:
            return ExtractedFrames(
                frames=[],
                skipped=[SkippedFrame(timestamp_seconds=0.0, reason=reason)],
                duration_seconds=0.0,
            )
        return ExtractedFrames(
            frames=[SelectedFrame(timestamp_seconds=0.0, image_bytes=processed)],
            skipped=[],
            duration_seconds=0.0,
        )

    if suffix not in VIDEO_SUFFIXES:
        raise InvalidVideoError("Upload must be an MP4, MOV, AVI, WEBM, or supported image.")

    temporary_path = None
    capture = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(media_bytes)
        capture = cv2.VideoCapture(temporary_path)
        if not capture.isOpened():
            raise InvalidVideoError("The uploaded video is corrupt or unreadable.")

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not np.isfinite(fps) or fps <= 0 or frame_count <= 0:
            raise InvalidVideoError("The uploaded video has invalid duration metadata.")
        duration = frame_count / fps
        if duration > max_video_seconds:
            raise InvalidVideoError(
                f"The video duration exceeds the {max_video_seconds:g}-second limit."
            )

        timestamps = list(np.arange(0, duration, interval_seconds, dtype=float))
        timestamps = timestamps[:max_frames]
        frames: list[SelectedFrame] = []
        skipped: list[SkippedFrame] = []
        previous_selected = None
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            success, frame_bgr = capture.read()
            if not success or frame_bgr is None:
                skipped.append(
                    SkippedFrame(
                        timestamp_seconds=float(timestamp),
                        reason="frame could not be decoded",
                    )
                )
                continue

            try:
                processed_bytes = _jpeg_bytes(frame_bgr)
            except InvalidVideoError as exc:
                skipped.append(
                    SkippedFrame(timestamp_seconds=float(timestamp), reason=str(exc))
                )
                continue
            processed_frame = cv2.imdecode(
                np.frombuffer(processed_bytes, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if processed_frame is None:
                skipped.append(
                    SkippedFrame(
                        timestamp_seconds=float(timestamp),
                        reason="preprocessed frame could not be decoded",
                    )
                )
                continue
            reason = _skip_quality_reason(processed_frame)
            if reason:
                skipped.append(
                    SkippedFrame(timestamp_seconds=float(timestamp), reason=reason)
                )
                continue
            if previous_selected is not None and _near_duplicate(
                processed_frame,
                previous_selected,
            ):
                skipped.append(
                    SkippedFrame(
                        timestamp_seconds=float(timestamp),
                        reason="frame skipped as a near-duplicate",
                    )
                )
                continue

            frames.append(
                SelectedFrame(
                    timestamp_seconds=float(timestamp),
                    image_bytes=processed_bytes,
                )
            )
            previous_selected = processed_frame
        if not frames and not skipped:
            raise InvalidVideoError("The video contains no readable frames.")
        return ExtractedFrames(
            frames=frames,
            skipped=skipped,
            duration_seconds=duration,
        )
    except cv2.error as exc:
        raise InvalidVideoError("The uploaded video is corrupt or unreadable.") from exc
    finally:
        if capture is not None:
            capture.release()
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
