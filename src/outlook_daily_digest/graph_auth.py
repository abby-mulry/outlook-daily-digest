from __future__ import annotations

from collections.abc import Callable

import msal

from .config import Settings, validate_read_only_scopes


class GraphAuthError(RuntimeError):
    """Raised when Microsoft Graph authentication fails."""


class GraphAuthenticator:
    def __init__(
        self,
        settings: Settings,
        message_callback: Callable[[str], None] | None = None,
    ) -> None:
        validate_read_only_scopes(settings.scopes)
        self.settings = settings
        self.message_callback = message_callback or print
        self.cache = msal.SerializableTokenCache()

        if settings.token_cache_path.exists():
            self.cache.deserialize(settings.token_cache_path.read_text(encoding="utf-8"))

        authority = f"https://login.microsoftonline.com/{settings.tenant_id}"
        self.app = msal.PublicClientApplication(
            client_id=settings.client_id,
            authority=authority,
            token_cache=self.cache,
        )

    def get_access_token(self) -> str:
        result = self._acquire_token_silently()
        if not result:
            result = self._acquire_token_by_device_flow()

        access_token = result.get("access_token")
        if not access_token:
            error = result.get("error_description") or result.get("error") or "unknown error"
            raise GraphAuthError(f"Microsoft Graph authentication failed: {error}")

        self._persist_cache()
        return access_token

    def authorization_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    def _acquire_token_silently(self) -> dict | None:
        accounts = self.app.get_accounts()
        if not accounts:
            return None
        return self.app.acquire_token_silent(self.settings.scopes, account=accounts[0])

    def _acquire_token_by_device_flow(self) -> dict:
        flow = self.app.initiate_device_flow(scopes=self.settings.scopes)
        if "user_code" not in flow:
            raise GraphAuthError("Could not create a Microsoft Graph device login flow.")

        self.message_callback(flow["message"])
        return self.app.acquire_token_by_device_flow(flow)

    def _persist_cache(self) -> None:
        if not self.cache.has_state_changed:
            return

        self.settings.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.token_cache_path.write_text(
            self.cache.serialize(),
            encoding="utf-8",
        )
