from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    auto_seed: bool
    owner_email: str | None
    owner_password: str | None
    seed_tags_path: Path
    vector_search_enabled: bool
    vector_provider: str
    vector_dir: Path
    vector_collection: str

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[4]

    @classmethod
    def load(cls) -> "Settings":
        repo_root = cls._repo_root()
        data_dir = repo_root / "data"
        db_path = data_dir / "db.sqlite"

        return cls(
            env=os.getenv("LETTEROPS_ENV", "local"),
            database_url=os.getenv("DATABASE_URL", f"sqlite:///{db_path}"),
            jwt_secret=os.getenv("LETTEROPS_JWT_SECRET", "change-me"),
            jwt_algorithm=os.getenv("LETTEROPS_JWT_ALG", "HS256"),
            access_token_ttl_minutes=int(os.getenv("LETTEROPS_JWT_ACCESS_MIN", "480")),
            refresh_token_ttl_days=int(os.getenv("LETTEROPS_JWT_REFRESH_DAYS", "30")),
            auto_seed=os.getenv("LETTEROPS_AUTO_SEED", "0") == "1",
            owner_email=os.getenv("LETTEROPS_OWNER_EMAIL"),
            owner_password=os.getenv("LETTEROPS_OWNER_PASSWORD"),
            seed_tags_path=Path(
                os.getenv(
                    "LETTEROPS_SEED_TAGS_PATH",
                    str(repo_root / "infra" / "seeds" / "tags.json"),
                )
            ),
            vector_search_enabled=os.getenv("LETTEROPS_VECTOR_SEARCH", "0") == "1",
            vector_provider=os.getenv("LETTEROPS_VECTOR_PROVIDER", "chroma"),
            vector_dir=Path(
                os.getenv("LETTEROPS_VECTOR_DIR", str(repo_root / "data" / "vectors"))
            ),
            vector_collection=os.getenv("LETTEROPS_VECTOR_COLLECTION", "documents"),
        )


settings = Settings.load()
