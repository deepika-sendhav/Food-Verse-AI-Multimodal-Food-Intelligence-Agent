from __future__ import annotations

import gzip
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}\b"),
    re.compile(
        r"""(?i)\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?)\b"""
        r"""\s*=\s*["']?"""
        r"""([A-Za-z0-9_/+=-]{12,})"""
    ),
    re.compile(
        r"""(?i)\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?)\b"""
        r""":\s*["']"""
        r"""([A-Za-z0-9_/+=-]{12,})["']"""
    ),
)
SAFE_PLACEHOLDERS = ("your_", "replace_", "example", "changeme", "placeholder", "dummy")
SENSITIVE_PATH_PARTS = {
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    "temp_uploads",
    "test_photos",
    "test_videos",
}
SENSITIVE_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
TEST_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def python_executable() -> str:
    candidates = (
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def repository_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_sensitive_path(path: str) -> bool:
    candidate = Path(path)
    parts = {part.casefold() for part in candidate.parts}
    name = candidate.name.casefold()
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if parts & SENSITIVE_PATH_PARTS:
        return True
    if candidate.suffix.casefold() in SENSITIVE_EXTENSIONS:
        return True
    if candidate.name.casefold().startswith(("test_photo", "test_video")):
        return True
    return "tests" in parts and candidate.suffix.casefold() in TEST_IMAGE_EXTENSIONS


def security_scan() -> tuple[list[str], list[str]]:
    paths = tracked_paths()
    secret_files: list[str] = []
    for relative_path in repository_paths():
        path = ROOT / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                candidate = match.group(1) if pattern.groups else match.group(0)
                if candidate.casefold().startswith(SAFE_PLACEHOLDERS):
                    continue
                if candidate.isupper() and "_" in candidate:
                    continue
                secret_files.append(relative_path)
                break
            if relative_path in secret_files:
                break
    sensitive_tracked = [path for path in paths if is_sensitive_path(path)]
    return sorted(set(secret_files)), sensitive_tracked


def check_ignore_rules() -> list[str]:
    samples = (
        "nested/.env",
        "nested/.venv/pyvenv.cfg",
        "nested/node_modules/example/index.js",
        "frontend/dist/index.html",
        "backend/__pycache__/main.pyc",
        "backend/temp_uploads/upload.bin",
        "demo.mp4",
        "demo.mov",
        "demo.avi",
        "demo.webm",
        "backend/tests/test_photos/sample.jpg",
        "backend/tests/test_videos/sample.mp4",
        "backend/tests/test_images/test_image.png",
        "test_video_sample.webm",
        "test_photo_sample.jpg",
    )
    failures = []
    for sample in samples:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", sample],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            failures.append(sample)
    return failures


def check_secrets_and_ignored() -> None:
    secrets, sensitive_tracked = security_scan()
    ignore_failures = check_ignore_rules()
    print("Tracked sensitive files: " + (", ".join(sensitive_tracked) or "none"))
    print("Potential secret files: " + (", ".join(secrets) or "none"))
    if secrets:
        raise RuntimeError("Potential hardcoded secrets found in: " + ", ".join(secrets))
    if sensitive_tracked:
        raise RuntimeError("Sensitive files are tracked: " + ", ".join(sensitive_tracked))
    if ignore_failures:
        raise RuntimeError("Required ignore rules missing for: " + ", ".join(ignore_failures))


def run_command(
    label: str,
    command: list[str],
    env: dict[str, str],
    cwd: Path = ROOT,
) -> None:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"{label} exited {result.returncode}:\n{output[-5000:]}")


def check_backend_health(python: str, env: dict[str, str]) -> None:
    with socket.socket() as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        port = server_socket.getsockname()[1]
    health_url = f"http://127.0.0.1:{port}/api/health"
    server_env = env.copy()
    server_env["DEMO_MODE"] = "true"
    server_env["CORS_ORIGINS"] = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    process = subprocess.Popen(
        [
            python,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=ROOT,
        env=server_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Backend process exited before health check.")
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
                    payload = json.loads(response.read())
                    if (
                        response.status != 200
                        or payload.get("status") != "ok"
                        or payload.get("demo") is not True
                    ):
                        raise RuntimeError("Health endpoint returned an unexpected response.")
                    return
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        raise RuntimeError("Backend health endpoint did not respond within 5 seconds.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def build_frontend(npm: str, env: dict[str, str]) -> None:
    run_command(
        "Frontend production build",
        [npm, "run", "build"],
        env,
        ROOT / "frontend",
    )
    assets = sorted((ROOT / "frontend" / "dist" / "assets").glob("*"))
    files = [path for path in assets if path.is_file()]
    raw_size = sum(path.stat().st_size for path in files)
    gzip_size = sum(len(gzip.compress(path.read_bytes())) for path in files)
    print(
        "Production bundle: "
        f"{len(files)} asset files, {raw_size / 1024:.1f} KiB raw, "
        f"{gzip_size / 1024:.1f} KiB gzip"
    )


def main() -> int:
    python = python_executable()
    npm = "npm.cmd" if os.name == "nt" else "npm"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "GROQ_API_KEY": "",
            "USDA_FDC_API_KEY": "",
            "DEMO_MODE": "false",
            "CORS_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
        }
    )
    checks: list[tuple[str, object]] = [
        ("Backend pytest", lambda: run_command(
            "Backend pytest",
            [python, "-m", "pytest", "backend/tests", "-q"],
            env,
        )),
        ("Frontend npm test", lambda: run_command(
            "Frontend npm test",
            [npm, "test"],
            env,
            ROOT / "frontend",
        )),
        ("Frontend production build", lambda: build_frontend(npm, env)),
        ("Python syntax", lambda: run_command(
            "Python syntax",
            [python, "-m", "compileall", "-q", "backend", "scripts"],
            env,
        )),
        ("Demo health startup", lambda: check_backend_health(python, env)),
        ("Secrets and ignore rules", check_secrets_and_ignored),
    ]
    results: list[tuple[str, bool, float, str]] = []
    for label, action in checks:
        started = time.perf_counter()
        try:
            action()
            results.append((label, True, time.perf_counter() - started, ""))
        except Exception as exc:
            results.append((label, False, time.perf_counter() - started, str(exc)))

    print(f"{'Check':<30} {'Result':<8} {'Time':>9}")
    print("-" * 51)
    for label, passed, duration, _detail in results:
        print(f"{label:<30} {'PASS' if passed else 'FAIL':<8} {duration:>8.2f}s")
    for label, passed, _duration, detail in results:
        if not passed:
            print(f"\n{label} failure:\n{detail}")
    failed = sum(not passed for _, passed, _, _ in results)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
