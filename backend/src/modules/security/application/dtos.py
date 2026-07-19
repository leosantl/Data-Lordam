from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.security.domain.entities import Role


@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class AuthenticateUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    email: str
    role: Role
    is_active: bool


@dataclass(frozen=True)
class AuthTokenResult:
    access_token: str
    token_type: str = "bearer"
