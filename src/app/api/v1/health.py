from typing import Annotated, Any
from fastapi import APIRouter, Depends, Request
from ...core.schemas import HealthCheck

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request) -> dict:
    health = HealthCheck(
        name="Hello FastAPI", version="1.0.0", description="Test service of FastAPI"
    )
    return health  # type: ignore
