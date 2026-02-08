import warnings

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing_roundtrip() -> None:
    password = "ExamplePass123"  # bcrypt hard limit 72 bytes
    hashed = hash_password(password)
    assert verify_password(password, hashed)


def test_access_token_contains_subject() -> None:
    token = create_access_token("user-1", "owner")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "owner"
    assert payload["type"] == "access"


def test_decode_token_suppresses_jose_utcnow_deprecation() -> None:
    token = create_access_token("user-2", "editor")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        payload = decode_token(token)
    assert payload["sub"] == "user-2"
    assert all("datetime.datetime.utcnow()" not in str(w.message) for w in caught)
