from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: uuid.UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class UserAuthenticated(DomainEvent):
    user_id: uuid.UUID


@dataclass(frozen=True, kw_only=True)
class PermissionDenied(DomainEvent):
    user_id: uuid.UUID
    action: str
