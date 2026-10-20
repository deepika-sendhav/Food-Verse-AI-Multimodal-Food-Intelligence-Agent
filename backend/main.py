from fastapi import FastAPI

from backend.routers.food_recognition import router as food_recognition_router
from backend.routers.freshness import router as freshness_router
from backend.routers.hygiene import router as hygiene_router
from backend.routers.kitchen_assistant import router as kitchen_assistant_router
from backend.routers.profile import router as profile_router

app = FastAPI()
app.include_router(food_recognition_router)
app.include_router(freshness_router)
app.include_router(hygiene_router)
app.include_router(kitchen_assistant_router)
app.include_router(profile_router)
