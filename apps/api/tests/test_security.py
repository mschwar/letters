from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing_roundtrip() -> None:
    password = "ExamplePass123"
    hashed = hash_password(password)
    assert verify_password(password, hashed)


def test_access_token_contains_subject() -> None:
    token = create_access_token("user-1", "owner")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "owner"
    assert payload["type"] == "access"
