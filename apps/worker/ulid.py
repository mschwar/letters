from __future__ import annotations

import os
import time


CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_base32(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        value, index = divmod(value, 32)
        chars.append(CROCKFORD_BASE32[index])
    return "".join(reversed(chars))


def new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    random_bytes = os.urandom(10)
    randomness = int.from_bytes(random_bytes, byteorder="big")
    value = (timestamp_ms << 80) | randomness
    return _encode_base32(value, 26)
