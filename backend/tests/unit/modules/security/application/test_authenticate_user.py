import pytest

from src.core.exceptions import InvalidCredentialsError
from src.infrastructure.event_bus import InMemoryEventBus
from src.modules.security.application.dtos import AuthenticateUserCommand, RegisterUserCommand
from src.modules.security.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.modules.security.application.use_cases.register_user import RegisterUserUseCase
from tests.unit.modules.security.application.fakes import (
    FakePasswordHasher,
    FakeTokenProvider,
    FakeUserRepository,
)


@pytest.fixture
async def repository():
    repo = FakeUserRepository()
    register = RegisterUserUseCase(repo, FakePasswordHasher(), InMemoryEventBus())
    await register.execute(RegisterUserCommand(email="user@example.com", password="right-pass"))
    return repo


async def test_authenticates_with_correct_credentials(repository):
    use_case = AuthenticateUserUseCase(
        repository, FakePasswordHasher(), FakeTokenProvider(), InMemoryEventBus()
    )

    result = await use_case.execute(
        AuthenticateUserCommand(email="user@example.com", password="right-pass")
    )

    assert result.access_token.startswith("token::")
    assert result.token_type == "bearer"


async def test_rejects_wrong_password(repository):
    use_case = AuthenticateUserUseCase(
        repository, FakePasswordHasher(), FakeTokenProvider(), InMemoryEventBus()
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(AuthenticateUserCommand(email="user@example.com", password="wrong"))


async def test_rejects_unknown_email(repository):
    use_case = AuthenticateUserUseCase(
        repository, FakePasswordHasher(), FakeTokenProvider(), InMemoryEventBus()
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            AuthenticateUserCommand(email="ghost@example.com", password="whatever")
        )


async def test_rejects_malformed_email(repository):
    use_case = AuthenticateUserUseCase(
        repository, FakePasswordHasher(), FakeTokenProvider(), InMemoryEventBus()
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(AuthenticateUserCommand(email="not-an-email", password="whatever"))
