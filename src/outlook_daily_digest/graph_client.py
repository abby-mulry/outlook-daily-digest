from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import requests

from .config import DEFAULT_GRAPH_BASE_URL
from .graph_auth import GraphAuthenticator


class ReadOnlyGraphClient:
    def __init__(
        self,
        authenticator: GraphAuthenticator,
        base_url: str = DEFAULT_GRAPH_BASE_URL,
        timeout_seconds: int = 30,
    ) -> None:
        self.authenticator = authenticator
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def get_json(
        self,
        path_or_url: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._url_for(path_or_url)
        request_headers = self.authenticator.authorization_header()
        if headers:
            request_headers.update(headers)

        response = self.session.get(
            url,
            params=params,
            headers=request_headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def paged_get(
        self,
        path_or_url: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        next_url: str | None = path_or_url
        next_params = params

        while next_url:
            payload = self.get_json(next_url, params=next_params, headers=headers)
            yield from payload.get("value", [])
            next_url = payload.get("@odata.nextLink")
            next_params = None

    def _url_for(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://"):
            return path_or_url
        path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
        return f"{self.base_url}{path}"
