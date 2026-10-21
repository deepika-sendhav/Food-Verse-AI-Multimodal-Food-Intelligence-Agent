from __future__ import annotations

import argparse
import io
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
MODEL_ENDPOINTS = (
    "/api/food-recognition/analyze",
    "/api/freshness/analyze",
    "/api/hygiene/analyze",
    "/api/kitchen/generate-recipe",
    "/api/meal-plan/generate",
)


def send_request(path: str, method: str = "GET", payload: bytes | None = None,
                 content_type: str | None = None, timeout: int = 30) -> tuple[int, dict]:
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        BASE_URL + path,
        data=payload,
        headers=headers,
        method=method,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            result = json.loads(response.read()) if response.headers.get("Content-Type", "").startswith("application/json") else {}
    except urllib.error.HTTPError as exc:
        status = exc.code
        result = {}
        exc.close()
    duration = time.perf_counter() - started
    display_path = "/api/profile/{profile_id}" if path.startswith("/api/profile/") else path
    print(f"{method} {display_path}: HTTP {status} ({duration:.2f}s)")
    return status, result


def json_request(path: str, payload: dict, method: str = "POST") -> tuple[int, dict]:
    return send_request(
        path,
        method,
        json.dumps(payload).encode("utf-8"),
        "application/json",
    )


def multipart_request(path: str, fields: dict[str, str], file_field: str | None = None,
                      filename: str = "", content_type: str = "",
                      file_bytes: bytes = b"",
                      timeout: int = 30) -> tuple[int, dict]:
    boundary = "FoodVerseSmokeBoundary"
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    if file_field is not None:
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
        )
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.write(file_bytes)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    return send_request(
        path,
        "POST",
        body.getvalue(),
        f"multipart/form-data; boundary={boundary}",
        timeout,
    )


def synthetic_jpeg() -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for --live synthetic image inputs.") from exc
    randomizer = random.Random(7)
    image = Image.new("RGB", (96, 96))
    image.putdata(
        [
            (70 + randomizer.randrange(120), 70 + randomizer.randrange(120), 35 + randomizer.randrange(100))
            for _ in range(96 * 96)
        ]
    )
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue()


def main() -> int:
    global BASE_URL
    parser = argparse.ArgumentParser(description="Run safe FoodVerse API smoke checks.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send one synthetic request to each model-backed endpoint.",
    )
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")

    health_status, _ = send_request("/api/health")
    options_status, _ = send_request("/api/profile/options")
    profile_data = {
        "age_years": 30,
        "sex": "female",
        "height": 165,
        "height_unit": "cm",
        "weight": 62,
        "weight_unit": "kg",
        "activity_level": "moderate",
        "health_goal": "maintain",
        "diet_type": "omnivore",
        "allergies": [],
        "food_restrictions": [],
        "dislikes": [],
        "medical_conditions": [],
        "pregnant_or_breastfeeding": None,
        "meals_per_day": 3,
        "cuisine_preferences": [],
    }
    validate_status, _ = json_request("/api/profile/validate", profile_data)
    profile_status, profile_response = json_request("/api/profile", profile_data)
    profile_id = profile_response.get("profile_id") if profile_status == 201 else None

    if args.live:
        print("LIVE MODE: synthetic inputs will be sent to configured model services.")
        image = synthetic_jpeg()
        multipart_request(
            MODEL_ENDPOINTS[0],
            {},
            "file",
            "demo.jpg",
            "image/jpeg",
            image,
            timeout=180,
        )
        multipart_request(
            MODEL_ENDPOINTS[1],
            {},
            "file",
            "demo.jpg",
            "image/jpeg",
            image,
            timeout=180,
        )
        multipart_request(
            MODEL_ENDPOINTS[2],
            {"interval_seconds": "5"},
            "file",
            "demo.jpg",
            "image/jpeg",
            image,
            timeout=180,
        )
        multipart_request(
            MODEL_ENDPOINTS[3],
            {
                "text_input": "Suggest a simple vegetable and lentil dinner.",
                "servings": "2",
                "skill_level": "beginner",
            },
            timeout=180,
        )
        if profile_id:
            json_request(
                MODEL_ENDPOINTS[4],
                {"profile_id": profile_id, "plan_type": "daily", "days": 1},
            )
    else:
        print("Live-model endpoints not called:")
        for endpoint in MODEL_ENDPOINTS:
            print(f"  {endpoint}")
        print("Use --live to send synthetic requests to configured model services.")

    if profile_id:
        delete_status, _ = send_request(f"/api/profile/{profile_id}", "DELETE")
    else:
        delete_status = 204
    checks = (health_status, options_status, validate_status, profile_status, delete_status)
    return 0 if all(200 <= status < 300 for status in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
