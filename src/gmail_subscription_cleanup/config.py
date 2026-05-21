from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DEFAULT_GMAIL_SCOPES = (GMAIL_READONLY_SCOPE,)


@dataclass(frozen=True)
class Settings:
    credentials_path: Path
    token_path: Path
    scopes: tuple[str, ...]
    user_id: str
    default_query: str


def parse_scopes(raw_scopes: str | None) -> tuple[str, ...]:
    if not raw_scopes:
        return DEFAULT_GMAIL_SCOPES

    normalized = raw_scopes.replace(",", " ")
    scopes = tuple(scope.strip() for scope in normalized.split() if scope.strip())
    return scopes or DEFAULT_GMAIL_SCOPES


def validate_read_only_scopes(scopes: tuple[str, ...]) -> None:
    unsupported_scopes = tuple(
        scope for scope in scopes if scope != GMAIL_READONLY_SCOPE
    )
    if unsupported_scopes:
        joined = ", ".join(unsupported_scopes)
        raise ValueError(
            "Only the Gmail read-only OAuth scope is allowed. "
            f"Remove or replace: {joined}"
        )


def load_settings(env_path: str | Path | None = None) -> Settings:
    _load_environment(env_path)

    scopes = parse_scopes(os.getenv("GMAIL_SCOPES"))
    validate_read_only_scopes(scopes)

    return Settings(
        credentials_path=Path(
            os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        ).expanduser(),
        token_path=Path(os.getenv("GMAIL_TOKEN_FILE", "token.json")).expanduser(),
        scopes=scopes,
        user_id=os.getenv("GMAIL_USER_ID", "me").strip() or "me",
        default_query=os.getenv("GMAIL_QUERY", "newer_than:90d").strip(),
    )


def _load_environment(env_path: str | Path | None = None) -> None:
    if _load_dotenv is not None:
        if env_path is not None:
            _load_dotenv(env_path)
        else:
            _load_dotenv()
        return

    path = Path(env_path) if env_path is not None else Path(".env")
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
