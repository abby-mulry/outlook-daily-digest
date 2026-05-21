from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import Settings, validate_read_only_scopes


class GmailAuthError(RuntimeError):
    """Raised when Gmail OAuth authentication fails."""


class GmailAuthenticator:
    def __init__(self, settings: Settings) -> None:
        validate_read_only_scopes(settings.scopes)
        self.settings = settings

    def get_credentials(self) -> Credentials:
        credentials = self._load_saved_credentials()
        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            credentials = self._run_oauth_flow()

        self._save_credentials(credentials)
        return credentials

    def build_service(self):
        return build(
            "gmail",
            "v1",
            credentials=self.get_credentials(),
            cache_discovery=False,
        )

    def _load_saved_credentials(self) -> Credentials | None:
        token_path = self.settings.token_path
        if not token_path.exists():
            return None

        _validate_token_file_scopes(token_path)
        return Credentials.from_authorized_user_file(
            str(token_path),
            scopes=list(self.settings.scopes),
        )

    def _run_oauth_flow(self) -> Credentials:
        credentials_path = self.settings.credentials_path
        if not credentials_path.exists():
            raise GmailAuthError(
                f"Gmail OAuth client file not found: {credentials_path}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            scopes=list(self.settings.scopes),
        )
        return flow.run_local_server(port=0)

    def _save_credentials(self, credentials: Credentials) -> None:
        token_path = self.settings.token_path
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")


def _validate_token_file_scopes(token_path: Path) -> None:
    try:
        payload = json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GmailAuthError(f"Could not parse Gmail token file: {token_path}") from exc

    raw_scopes = payload.get("scopes") or payload.get("scope") or ()
    if isinstance(raw_scopes, str):
        scopes = tuple(raw_scopes.split())
    else:
        scopes = tuple(str(scope) for scope in raw_scopes)

    if scopes:
        validate_read_only_scopes(scopes)
