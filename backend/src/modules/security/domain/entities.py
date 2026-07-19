from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.shared_kernel.email import Email


class Role(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    AUDITOR = "auditor"


@dataclass
class User:
    email: Email
    hashed_password: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: Role = Role.VIEWER
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def deactivate(self) -> None:
        self.is_active = False

    def can(self, action_min_role: Role) -> bool:
        order = [Role.AUDITOR, Role.VIEWER, Role.EDITOR, Role.OWNER]
        return order.index(self.role) >= order.index(action_min_role)
