import pytest

from src.shared_kernel.email import Email


def test_normalizes_case_and_whitespace():
    email = Email("  User@Example.COM  ")
    assert str(email) == "user@example.com"


def test_equality_by_value():
    assert Email("a@b.com") == Email("a@b.com")


@pytest.mark.parametrize("invalid", ["not-an-email", "missing-domain@", "@missing-local.com", ""])
def test_rejects_invalid_format(invalid):
    with pytest.raises(ValueError):
        Email(invalid)
