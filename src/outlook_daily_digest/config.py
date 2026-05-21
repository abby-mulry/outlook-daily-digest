from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None


DEFAULT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_READ_ONLY_SCOPES = ("User.Read", "Mail.Read", "Calendars.Read")
ALLOWED_READ_ONLY_SCOPES = frozenset(
    {
        "User.Read",
        "Mail.Read",
        "Mail.ReadBasic",
        "Mail.Read.Shared",
        "Mail.ReadBasic.Shared",
        "Calendars.Read",
        "Calendars.Read.Shared",
    }
)


@dataclass(frozen=True)
class Settings:
    client_id: str
    tenant_id: str
    scopes: tuple[str, ...]
    graph_base_url: str
    token_cache_path: Path
    outlook_timezone: str


def parse_scopes(raw_scopes: str | None) -> tuple[str, ...]:
    if not raw_scopes:
        return DEFAULT_READ_ONLY_SCOPES

    normalized = raw_scopes.replace(",", " ")
    scopes = tuple(scope.strip() for scope in normalized.split() if scope.strip())
    return scopes or DEFAULT_READ_ONLY_SCOPES


def validate_read_only_scopes(scopes: tuple[str, ...]) -> None:
    mutating_scopes = tuple(
        scope for scope in scopes if scope not in ALLOWED_READ_ONLY_SCOPES
    )
    if mutating_scopes:
        joined = ", ".join(mutating_scopes)
        raise ValueError(
            "Only read-only Microsoft Graph scopes are allowed. "
            f"Remove or replace: {joined}"
        )


def load_settings(env_path: str | Path | None = None) -> Settings:
    _load_environment(env_path)

    scopes = parse_scopes(os.getenv("MS_GRAPH_SCOPES"))
    validate_read_only_scopes(scopes)

    client_id = os.getenv("MS_GRAPH_CLIENT_ID", "").strip()
    if not client_id:
        raise ValueError("MS_GRAPH_CLIENT_ID is required in your environment or .env file.")

    token_cache_path = Path(
        os.getenv("MS_GRAPH_TOKEN_CACHE", ".msal_token_cache.json")
    ).expanduser()

    return Settings(
        client_id=client_id,
        tenant_id=os.getenv("MS_GRAPH_TENANT_ID", "common").strip() or "common",
        scopes=scopes,
        graph_base_url=os.getenv("MS_GRAPH_BASE_URL", DEFAULT_GRAPH_BASE_URL).rstrip("/"),
        token_cache_path=token_cache_path,
        outlook_timezone=os.getenv("OUTLOOK_TIMEZONE", "UTC").strip() or "UTC",
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
