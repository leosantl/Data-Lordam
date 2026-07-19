from __future__ import annotations

from src.core.events import EventBus
from src.core.exceptions import EntityAlreadyExistsError
from src.modules.security.application.dtos import RegisterUserCommand, UserView
from src.modules.security.application.ports import PasswordHasher
from src.modules.security.domain.entities import User
from src.modules.security.domain.events import UserRegistered
from src.modules.security.domain.repositories import UserRepository
from src.shared_kernel.email import Email


class RegisterUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        event_bus: EventBus,
    ) -> None:
        self._users = user_repository
        self._hasher = password_hasher
        self._event_bus = event_bus

    async def execute(self, command: RegisterUserCommand) -> UserView:
        email = Email(command.email)

        if await self._users.get_by_email(email) is not None:
            raise EntityAlreadyExistsError("User", "email", str(email))

        user = User(email=email, hashed_password=self._hasher.hash(command.password))
        await self._users.add(user)

        await self._event_bus.publish(UserRegistered(user_id=user.id, email=str(user.email)))

        return UserView(id=user.id, email=str(user.email), role=user.role, is_active=user.is_active)
