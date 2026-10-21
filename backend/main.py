import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import CORS_ORIGINS, DEMO_MODE
from backend.routers.food_recognition import router as food_recognition_router
from backend.routers.freshness import router as freshness_router
from backend.routers.hygiene import router as hygiene_router
from backend.routers.kitchen_assistant import router as kitchen_assistant_router
from backend.routers.meal_planner import router as meal_planner_router
from backend.routers.profile import router as profile_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )


@app.get("/api/health")
async def health() -> dict[str, object]:
    result: dict[str, object] = {
        "status": "ok",
        "demo": DEMO_MODE,
        "configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
    }
    if DEMO_MODE:
        result["demo_warning"] = (
            "Demo mode: sample data only. No real analysis was performed."
        )
    return result


app.include_router(food_recognition_router)
app.include_router(freshness_router)
app.include_router(hygiene_router)
app.include_router(kitchen_assistant_router)
app.include_router(profile_router)
app.include_router(meal_planner_router)
