import pytest

from src.core.exceptions import EntityAlreadyExistsError
from src.infrastructure.event_bus import InMemoryEventBus
from src.modules.security.application.dtos import RegisterUserCommand
from src.modules.security.application.use_cases.register_user import RegisterUserUseCase
from src.modules.security.domain.events import UserRegistered
from tests.unit.modules.security.application.fakes import FakePasswordHasher, FakeUserRepository


@pytest.fixture
def use_case():
    return RegisterUserUseCase(FakeUserRepository(), FakePasswordHasher(), InMemoryEventBus())


async def test_registers_new_user(use_case):
    result = await use_case.execute(RegisterUserCommand(email="new@example.com", password="s3cret"))

    assert result.email == "new@example.com"
    assert result.is_active is True


async def test_rejects_duplicate_email():
    repository = FakeUserRepository()
    use_case = RegisterUserUseCase(repository, FakePasswordHasher(), InMemoryEventBus())
    await use_case.execute(RegisterUserCommand(email="dup@example.com", password="s3cret"))

    with pytest.raises(EntityAlreadyExistsError):
        await use_case.execute(RegisterUserCommand(email="dup@example.com", password="other"))


async def test_publishes_user_registered_event():
    events: list[UserRegistered] = []
    bus = InMemoryEventBus()

    async def capture(event: UserRegistered) -> None:
        events.append(event)

    bus.subscribe(UserRegistered.__name__, capture)

    use_case = RegisterUserUseCase(FakeUserRepository(), FakePasswordHasher(), bus)
    await use_case.execute(RegisterUserCommand(email="ev@example.com", password="s3cret"))

    assert len(events) == 1
    assert events[0].email == "ev@example.com"
