from __future__ import annotations

import uuid
from typing import Protocol

from src.modules.security.domain.entities import Role


class PasswordHasher(Protocol):
    def hash(self, plain_password: str) -> str: ...

    def verify(self, plain_password: str, hashed_password: str) -> bool: ...


class TokenProvider(Protocol):
    def issue_access_token(self, user_id: uuid.UUID, role: Role) -> str: ...

    def decode_access_token(self, token: str) -> uuid.UUID: ...
