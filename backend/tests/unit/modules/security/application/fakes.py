from __future__ import annotations

import uuid

from src.modules.security.domain.entities import Role, User
from src.shared_kernel.email import Email


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, User] = {}

    async def add(self, user: User) -> None:
        self._by_id[user.id] = user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._by_id.values():
            if user.email == email:
                return user
        return None


class FakePasswordHasher:
    def hash(self, plain_password: str) -> str:
        return f"hashed::{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed::{plain_password}"


class FakeTokenProvider:
    def __init__(self) -> None:
        self.issued_for: list[tuple[uuid.UUID, Role]] = []

    def issue_access_token(self, user_id: uuid.UUID, role: Role) -> str:
        self.issued_for.append((user_id, role))
        return f"token::{user_id}"

    def decode_access_token(self, token: str) -> uuid.UUID:
        return uuid.UUID(token.removeprefix("token::"))
