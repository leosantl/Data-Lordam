from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.di import get_event_bus
from src.core.events import EventBus
from src.core.exceptions import InvalidCredentialsError
from src.infrastructure.db import get_session
from src.modules.security.application.ports import PasswordHasher, TokenProvider
from src.modules.security.domain.entities import User
from src.modules.security.domain.repositories import UserRepository
from src.modules.security.infrastructure.jwt_token_provider import JwtTokenProvider
from src.modules.security.infrastructure.password_hasher import BcryptPasswordHasher
from src.modules.security.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_token_provider(settings: Annotated[Settings, Depends(get_settings)]) -> TokenProvider:
    return JwtTokenProvider(settings)


async def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    tokens: Annotated[TokenProvider, Depends(get_token_provider)],
) -> User:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        user_id = tokens.decode_access_token(token)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return user


__all__ = [
    "get_user_repository",
    "get_password_hasher",
    "get_token_provider",
    "get_current_user",
    "get_event_bus",
    "EventBus",
]
