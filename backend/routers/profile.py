import logging
from datetime import datetime
from typing import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from backend.schemas import UserProfile, UserProfileInput, UserProfileOptions
from backend.services.user_profile import (
    CANONICAL_ALLERGENS,
    ProfileCapacityError,
    ProfileValidationError,
    normalize_profile,
    profile_repository,
)

logger = logging.getLogger(__name__)


class PrivateProfileRoute(APIRoute):
    def get_route_handler(self) -> Callable[..., Response]:
        original_handler = super().get_route_handler()

        async def private_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
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
    prefix="/api/profile",
    tags=["user profile"],
    route_class=PrivateProfileRoute,
)


def _normalize_or_422(
    data: UserProfileInput,
    *,
    profile_id: UUID | None = None,
    created_at: datetime | None = None,
) -> UserProfile:
    try:
        return normalize_profile(
            data,
            profile_id=profile_id,
            created_at=created_at,
        )
    except ProfileValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors) from exc


@router.post("/validate", response_model=UserProfile)
async def validate_profile(data: UserProfileInput) -> UserProfile:
    return _normalize_or_422(data)


@router.post("", response_model=UserProfile, status_code=201)
async def create_profile(data: UserProfileInput) -> UserProfile:
    profile = _normalize_or_422(data)
    try:
        profile_repository.save(profile)
    except ProfileCapacityError as exc:
        logger.warning("%s profile_id=%s", type(exc).__name__, profile.profile_id)
        raise HTTPException(
            status_code=503,
            detail="Profile storage is temporarily full.",
        ) from exc
    return profile


@router.get("/options", response_model=UserProfileOptions)
async def profile_options() -> UserProfileOptions:
    return UserProfileOptions(
        sexes=["female", "male", "other", "prefer_not_to_say"],
        activity_levels=["sedentary", "light", "moderate", "active", "very_active"],
        health_goals=[
            "maintain",
            "lose_weight",
            "gain_weight",
            "build_muscle",
            "eat_healthier",
        ],
        diet_types=[
            "omnivore",
            "vegetarian",
            "vegan",
            "pescatarian",
            "eggetarian",
            "jain",
            "halal",
            "kosher",
            "other",
        ],
        canonical_allergens=list(CANONICAL_ALLERGENS),
        height_units=["cm", "in"],
        weight_units=["kg", "lb"],
    )


@router.get("/{profile_id}", response_model=UserProfile)
async def get_profile(profile_id: UUID) -> UserProfile:
    profile = profile_repository.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile


@router.put("/{profile_id}", response_model=UserProfile)
async def update_profile(profile_id: UUID, data: UserProfileInput) -> UserProfile:
    existing = profile_repository.get(profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile = _normalize_or_422(
        data,
        profile_id=profile_id,
        created_at=existing.created_at,
    )
    if not profile_repository.replace(profile):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: UUID) -> Response:
    if not profile_repository.delete(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return Response(status_code=204)
