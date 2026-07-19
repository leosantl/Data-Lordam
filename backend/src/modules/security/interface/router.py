from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.events import EventBus
from src.core.exceptions import EntityAlreadyExistsError, InvalidCredentialsError
from src.modules.security.application.dtos import AuthenticateUserCommand, RegisterUserCommand
from src.modules.security.application.ports import PasswordHasher, TokenProvider
from src.modules.security.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.modules.security.application.use_cases.register_user import RegisterUserUseCase
from src.modules.security.domain.entities import User
from src.modules.security.domain.repositories import UserRepository
from src.modules.security.interface.dependencies import (
    get_current_user,
    get_event_bus,
    get_password_hasher,
    get_token_provider,
    get_user_repository,
)
from src.modules.security.interface.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> UserResponse:
    use_case = RegisterUserUseCase(users, hasher, event_bus)
    try:
        result = await use_case.execute(RegisterUserCommand(email=body.email, password=body.password))
    except EntityAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    return UserResponse(id=result.id, email=result.email, role=result.role, is_active=result.is_active)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    users: Annotated[UserRepository, Depends(get_user_repository)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    tokens: Annotated[TokenProvider, Depends(get_token_provider)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> TokenResponse:
    use_case = AuthenticateUserUseCase(users, hasher, tokens, event_bus)
    try:
        result = await use_case.execute(AuthenticateUserCommand(email=body.email, password=body.password))
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return TokenResponse(access_token=result.access_token, token_type=result.token_type)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=str(current_user.email),
        role=current_user.role,
        is_active=current_user.is_active,
    )
