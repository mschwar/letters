from __future__ import annotations

from typing import Any


def envelope(data: Any | None = None, error: Any | None = None, meta: dict | None = None) -> dict:
    return {
        "data": data,
        "error": error,
        "meta": meta or {},
    }
