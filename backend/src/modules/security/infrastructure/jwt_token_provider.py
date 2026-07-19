from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from src.core.config import Settings
from src.core.exceptions import InvalidCredentialsError
from src.modules.security.domain.entities import Role


class JwtTokenProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_access_token(self, user_id: uuid.UUID, role: Role) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "iat": now,
            "exp": now + timedelta(minutes=self._settings.jwt_access_token_expire_minutes),
        }
        return jwt.encode(payload, self._settings.jwt_secret_key, algorithm=self._settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> uuid.UUID:
        try:
            payload = jwt.decode(
                token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm]
            )
            return uuid.UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise InvalidCredentialsError()
