from __future__ import annotations

from src.core.events import EventBus
from src.core.exceptions import InvalidCredentialsError
from src.modules.security.application.dtos import AuthenticateUserCommand, AuthTokenResult
from src.modules.security.application.ports import PasswordHasher, TokenProvider
from src.modules.security.domain.events import UserAuthenticated
from src.modules.security.domain.repositories import UserRepository
from src.shared_kernel.email import Email


class AuthenticateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
        event_bus: EventBus,
    ) -> None:
        self._users = user_repository
        self._hasher = password_hasher
        self._tokens = token_provider
        self._event_bus = event_bus

    async def execute(self, command: AuthenticateUserCommand) -> AuthTokenResult:
        try:
            email = Email(command.email)
        except ValueError:
            raise InvalidCredentialsError()

        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()

        if not self._hasher.verify(command.password, user.hashed_password):
            raise InvalidCredentialsError()

        await self._event_bus.publish(UserAuthenticated(user_id=user.id))

        token = self._tokens.issue_access_token(user.id, user.role)
        return AuthTokenResult(access_token=token)
