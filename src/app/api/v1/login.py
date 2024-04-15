from datetime import timedelta, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.logger import logging
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.schemas import Token, LoginResponse, BackendTokens, UserDetails
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    security_scheme
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["login"])


@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(
        response: Response,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(async_get_db)],
) -> LoginResponse:
    user = await authenticate_user(username_or_email=form_data.username, password=form_data.password, db=db)
    logger.error(user)
    if not user:
        raise UnauthorizedException("Wrong username, email or password.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_expires_at = datetime.now(timezone.utc) + access_token_expires
    access_token = await create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    refresh_token = await create_refresh_token(data={"sub": user["username"]})
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_expires_at = datetime.now(timezone.utc) + refresh_token_expires

    return LoginResponse(
        user=UserDetails(
            name=user["name"],
            username=user["username"],
            email=user["email"],
            profile_image_url=user["profile_image_url"],
        ),
        backend_tokens=BackendTokens(
            access_token=Token(
                access_token=access_token,
                token_type="bearer",
                expires_at=access_expires_at.isoformat() + 'Z'
            ),
            refresh_token=Token(
                access_token=refresh_token,
                token_type="bearer",
                expires_at=refresh_expires_at.isoformat() + 'Z'
            )
        )
    )


# This is only for swagger UI to obtain the token for future authenticated calls. It requires the response with one
# access_token as key containing the token.
@router.post("/token", response_model=Token)
async def get_access_token(
        response: Response,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(async_get_db)],
) -> Token:
    user = await authenticate_user(username_or_email=form_data.username, password=form_data.password, db=db)
    if not user:
        raise UnauthorizedException("Wrong username, email or password.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_expires_at = datetime.now(timezone.utc) + access_token_expires
    access_token = await create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=access_expires_at.isoformat() + 'Z'
    )


@router.post("/refresh", dependencies=[Depends(security_scheme)])
async def refresh_access_token(request: Request, db: AsyncSession = Depends(async_get_db)) -> BackendTokens:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise UnauthorizedException("Authorization header missing.")

    if not auth_header.startswith("Bearer "):
        raise UnauthorizedException("Authorization header must start with 'Bearer '")

    refresh_token = auth_header[7:]  # Remove "Bearer " prefix to isolate the token
    if not refresh_token:
        raise UnauthorizedException("Refresh token missing.")

    user_data = await verify_token(refresh_token, db)
    if not user_data:
        raise UnauthorizedException("Invalid refresh token.")

    new_access_token = await create_access_token(data={"sub": user_data.username_or_email})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_expires_at = datetime.now(timezone.utc) + access_token_expires

    return BackendTokens(
        access_token=Token(
            access_token=new_access_token,
            token_type="bearer",
            expires_at=access_expires_at.isoformat() + 'Z'
        ),
        refresh_token=Token(
            access_token=refresh_token,
            token_type="bearer",
            expires_at=""
        )
    )
