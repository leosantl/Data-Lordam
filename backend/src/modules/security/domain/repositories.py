from __future__ import annotations

import uuid
from typing import Protocol

from src.modules.security.domain.entities import User
from src.shared_kernel.email import Email


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...
