from src.modules.security.domain.entities import Role, User
from src.shared_kernel.email import Email


def _make_user(role: Role = Role.VIEWER) -> User:
    return User(email=Email("user@example.com"), hashed_password="hashed", role=role)


def test_deactivate_flips_is_active():
    user = _make_user()
    assert user.is_active is True

    user.deactivate()

    assert user.is_active is False


def test_owner_can_do_everything():
    owner = _make_user(Role.OWNER)
    assert owner.can(Role.VIEWER)
    assert owner.can(Role.EDITOR)
    assert owner.can(Role.OWNER)


def test_viewer_cannot_do_editor_actions():
    viewer = _make_user(Role.VIEWER)
    assert viewer.can(Role.VIEWER)
    assert not viewer.can(Role.EDITOR)
    assert not viewer.can(Role.OWNER)
