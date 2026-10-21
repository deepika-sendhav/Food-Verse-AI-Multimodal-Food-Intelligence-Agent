# FoodVerse AI

FoodVerse AI is a multimodal kitchen-assistance demo: a FastAPI backend
provides food, freshness, hygiene, recipe, profile, and meal-planning APIs; a
Vite + React frontend presents the workflows in a responsive interface.

## Features

- Food recognition with estimated nutrition and clearly stated uncertainty.
- Rule-based freshness cues, optionally combined with vision analysis.
- Kitchen hygiene review for images and short videos.
- Recipe suggestions with cook mode and browser-only speech dictation.
- In-memory dietary profiles, safety review gates, and daily/weekly plans.
- Schema-validated demo responses that work without model credentials.
- No UI framework dependency; CSS variables support light and dark themes.

## Requirements

- Python 3.10 or newer (3.11 recommended).
- Node.js 20 or newer and npm.
- Backend dependencies from `requirements.txt`. Video processing may also
  require the system codecs supported by OpenCV.
- A Groq key is optional for rule-based features and required for live
  model-backed analysis. USDA FoodData Central access is optional.

## Windows setup and run

Create and activate a Python virtual environment from PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit the root `.env` to enable live model calls. Never commit `.env` or put
credentials in frontend variables. Start the backend in **Terminal 1**:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Install and start the frontend in **Terminal 2**:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

Open the Vite address shown in the terminal. During development, `/api` is
proxied to the backend. For production, set `VITE_API_BASE_URL` to the public
backend origin and configure backend CORS for the exact frontend origin.

## Architecture

```text
Browser
  └─ React + Vite frontend
       ├─ Lazy-loaded routes and shared accessible components
       └─ fetch API modules ── /api (Vite proxy in development) ──┐
                                                                  v
                                                            FastAPI backend
       ┌──────────────────────┬──────────────────┬───────────────┤
       food/freshness/hygiene │ kitchen assistant│ profiles/plans
       └──────────────────────┴──────────────────┴───────────────┘
              │                      │
       local rule/nutrition   optional Groq vision/language
       reference pipelines        and optional USDA lookup
```

## Environment variables

Copy `.env.example` to the repository root `.env`. Each variable is commented
there. Configure host secrets in the deployment provider, never in source
control.

| Variable | Safe/default value | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | empty | Optional live model credential; empty means unconfigured. |
| `GROQ_VISION_MODEL` | `qwen/qwen3.8-27b` | Groq model identifier. |
| `GROQ_TIMEOUT_SECONDS` | `30` | Per-request model timeout. |
| `FOOD_IMAGE_MAX_BYTES` | `10485760` | Maximum image upload size. |
| `FOOD_IMAGE_MAX_SIDE` | `2048` | Processed image dimension limit. |
| `HYGIENE_VIDEO_MAX_BYTES` | `52428800` | Maximum video upload size. |
| `HYGIENE_VIDEO_MAX_SECONDS` | `120` | Maximum video duration. |
| `HYGIENE_MAX_FRAMES` | `12` | Maximum selected hygiene frames. |
| `HYGIENE_MAX_CONCURRENCY` | `1` | Concurrent hygiene model requests. |
| `HYGIENE_FRAME_DELAY_SECONDS` | `2` | Delay between selected frames. |
| `HYGIENE_FRAME_MAX_SIDE` | `768` | Processed video-frame dimension limit. |
| `PROFILE_TTL_MINUTES` | `60` | In-memory profile expiration time. |
| `USDA_FDC_API_KEY` | empty | Optional USDA FoodData Central credential. |
| `DEMO_MODE` | `false` | Return labeled synthetic samples instead of live analysis. |
| `CORS_ORIGINS` | Vite localhost origins | Comma-separated exact browser origins; wildcard is rejected. |
| `VITE_API_BASE_URL` | empty | Frontend API origin; empty uses the development proxy. |

## Checks and demo mode

Run the full local validation from the repository root:

```powershell
python scripts/check_all.py
```

It runs the backend tests, frontend tests/build, syntax checks, a temporary
demo-mode backend health probe, a secret scan, and `.gitignore` checks. The
checks do not call Groq or USDA. With the backend already running, verify the
non-model endpoints using:

```powershell
python scripts/smoke_test.py
```

`python scripts/smoke_test.py --live` sends synthetic inputs to live
model-backed endpoints and may consume quota. To demonstrate without network
model calls, set `DEMO_MODE=true` in the root `.env` and restart the backend.
The app displays a persistent banner and all model-backed results are synthetic
examples. Switch back to `DEMO_MODE=false` and restart to return to live mode.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Backend readiness, demo flag, model configuration status. |
| POST | `/api/food-recognition/analyze` | Food image and nutrition estimate. |
| POST | `/api/freshness/analyze` | Image freshness assessment. |
| POST | `/api/freshness/features` | Image feature measurements. |
| POST | `/api/hygiene/analyze` | Kitchen image/video review. |
| POST | `/api/kitchen/generate-recipe` | Recipe generation from text or image. |
| GET | `/api/profile/options` | Profile option lists. |
| POST | `/api/profile/validate` | Validate and normalize a profile without storing. |
| POST | `/api/profile` | Create an in-memory profile. |
| GET/PUT/DELETE | `/api/profile/{profile_id}` | Read, update, or delete an in-memory profile. |
| POST | `/api/meal-plan/generate` | Generate a daily or weekly meal plan. |

## Limitations, disclaimers, and privacy

Model output and nutrition values are estimates, not medical or dietetic
advice. Visual freshness and hygiene checks cannot detect pathogens, toxins,
or every unsafe condition; they are not food-safety certification. Consult
qualified professionals and official food-safety guidance when appropriate.

Profiles are held in backend memory and expire; restarting the backend clears
them. Uploaded image bytes are processed in memory. Video frame extraction
uses a generated temporary filename and removes its temporary file after
processing; user-provided filenames are not used as disk paths. Do not upload
private or sensitive media to a live model service unless you have permission
and understand that provider's data practices. Demo responses are synthetic
and must never be represented as real analysis.

## Demo and deployment guides

- [Five-to-seven-minute demo walkthrough](docs/DEMO_SCRIPT.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Final readiness checklist](docs/FINAL_CHECKLIST.md)
