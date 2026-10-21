import logging
from typing import Callable

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from backend.config import DEMO_MODE
from backend.schemas import (
    MealMacroBalance,
    MealPlanRequest,
    MealPlanResponse,
    WeeklyMealReport,
)
from backend.services.demo_responses import load_demo_response
from backend.services.meal_planner import (
    ModelRateLimitedError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    create_meal_plan,
)
from backend.services.user_profile import profile_repository

logger = logging.getLogger(__name__)


class PrivateMealPlanRoute(APIRoute):
    def get_route_handler(self) -> Callable[..., Response]:
        original_handler = super().get_route_handler()

        async def private_handler(request: Request) -> Response:
            try:
                response = await original_handler(request)
                return response
            except RequestValidationError as exc:
                errors = [
                    {
                        "loc": error["loc"],
                        "msg": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ]
                return JSONResponse(status_code=422, content={"detail": errors})

        return private_handler


router = APIRouter(
    prefix="/api/meal-plan",
    tags=["meal planning"],
    route_class=PrivateMealPlanRoute,
)


@router.post("/generate", response_model=MealPlanResponse)
async def generate_meal_plan(request: MealPlanRequest) -> MealPlanResponse | JSONResponse:
    profile = profile_repository.get(request.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    if DEMO_MODE:
        response = load_demo_response(
            "safety_gate" if profile.requires_professional_review else "meal_plan",
            MealPlanResponse,
        )
        response.plan_type = request.plan_type
        if request.plan_type == "weekly":
            response.days = [
                response.days[0].model_copy(update={"day_number": day}, deep=True)
                for day in range(1, request.days + 1)
            ]
            response.weekly_report = WeeklyMealReport(
                average_daily_calories=1490,
                average_calories_difference_percent=-27.3,
                average_macro_balance=MealMacroBalance(
                    carbs=62.9,
                    protein=16.7,
                    fat=20.4,
                ),
                variety_score=0.111,
                days_within_10_percent_of_target=0,
                concern_areas=[
                    "Repeated sample meals demonstrate limited variety.",
                    "Sample daily calories differ from the illustrative target.",
                ],
                highlights=[],
            )
        return response
    try:
        return await create_meal_plan(request, profile)
    except ModelRateLimitedError as exc:
        logger.warning("%s", type(exc).__name__)
        headers = (
            {"Retry-After": exc.retry_after}
            if exc.retry_after is not None
            else None
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": "The meal planning service is rate limited; please try again shortly."
            },
            headers=headers,
        )
    except ModelTimeoutError as exc:
        logger.warning("%s", type(exc).__name__)
        raise HTTPException(
            status_code=504,
            detail="The meal planning service timed out.",
        ) from exc
    except ModelUnavailableError as exc:
        logger.warning("%s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="The meal planning service is unavailable.",
        ) from exc
    except ModelResponseError as exc:
        if exc.truncated:
            detail = "The meal planning model response was truncated; please retry."
        else:
            detail = "The meal planning service returned an invalid response."
        raise HTTPException(
            status_code=502,
            detail=detail,
        ) from exc
