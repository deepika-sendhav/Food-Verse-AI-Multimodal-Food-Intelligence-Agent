from fastapi import FastAPI

from backend.routers.food_recognition import router as food_recognition_router

app = FastAPI()
app.include_router(food_recognition_router)