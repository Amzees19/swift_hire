import pytest

from app.routes.public import _is_valid_email, _is_valid_password


@pytest.mark.parametrize(
    "email,expected",
    [
        ("user@example.com", True),
        ("user_useme1223@example.com", True),
        ("User.Name+tag@example.co.uk", True),
        ("  user@example.com  ", True),  # trims spaces
        ("bademail", False),
        ("", False),
        ("user@no-tld", False),
        ("user @example.com", False),
        ('@gmail.com', False),
        ("user@xn--exmple-cua.com", False),
        ("name@mail.example-domain.co.uk", True),
        ("user..name@example.com", False),
        ("user@.example.com", False),
        ("a" * 30 + "@example.com", True),  # long but under limits
    ],
)
def test_is_valid_email(email: str, expected: bool):
    assert _is_valid_email(email) is expected


@pytest.mark.parametrize(
    "pw,expected",
    [
        ("Passw0rd", True),
        ("abc12345", True),
        ("Abcdef12", True),       # exactly 8 chars
        ("A" * 23 + "1a", True),  # 25 chars
        ("short1", False),          # too short
        ("nospaces 1", False),      # spaces stripped should fail pattern
        ("  Passw0rd  ", False),    # whitespace not allowed
        ("Passw0rd\n", False),      # newline/whitespace not allowed
        ("lettersOnly", False),
        ("12345678", False),
        ("", False),
        ("Abcdef1", False),
        ("Abcdef1!", True),

        ("pass word1", False),
        ("a" * 26 + "1", False),    # too long
    ],
)
def test_is_valid_password(pw: str, expected: bool):
    assert _is_valid_password(pw) is expected
