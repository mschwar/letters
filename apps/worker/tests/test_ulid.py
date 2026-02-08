from apps.worker.ulid import new_ulid


def test_ulid_format() -> None:
    value = new_ulid()
    assert len(value) == 26
    assert value.isalnum()
