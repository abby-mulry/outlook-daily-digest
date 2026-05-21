from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any


METADATA_HEADERS = (
    "From",
    "Subject",
    "Date",
    "List-Unsubscribe",
    "List-Unsubscribe-Post",
    "List-ID",
    "List-Help",
    "List-Owner",
    "List-Post",
    "List-Subscribe",
    "Precedence",
)


@dataclass(frozen=True)
class GmailMessage:
    id: str
    thread_id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: str
    snippet: str
    label_ids: tuple[str, ...]
    headers: dict[str, str] = field(default_factory=dict)


class GmailInboxReader:
    def __init__(self, gmail_service: Any, user_id: str = "me") -> None:
        self.gmail_service = gmail_service
        self.user_id = user_id

    def list_messages(
        self,
        max_results: int = 250,
        query: str | None = None,
    ) -> list[GmailMessage]:
        if max_results < 1:
            return []

        message_refs = self._list_message_refs(max_results=max_results, query=query)
        return [self.get_message(message_ref["id"]) for message_ref in message_refs]

    def get_message(self, message_id: str) -> GmailMessage:
        payload = (
            self.gmail_service.users()
            .messages()
            .get(
                userId=self.user_id,
                id=message_id,
                format="metadata",
                metadataHeaders=list(METADATA_HEADERS),
            )
            .execute()
        )
        return message_from_gmail(payload)

    def _list_message_refs(
        self,
        max_results: int,
        query: str | None,
    ) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        next_page_token: str | None = None

        while len(refs) < max_results:
            batch_size = min(500, max_results - len(refs))
            request = (
                self.gmail_service.users()
                .messages()
                .list(
                    userId=self.user_id,
                    labelIds=["INBOX"],
                    includeSpamTrash=False,
                    maxResults=batch_size,
                    q=query,
                    pageToken=next_page_token,
                )
            )
            response = request.execute()
            refs.extend(response.get("messages", []))
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return refs[:max_results]


def message_from_gmail(item: dict[str, Any]) -> GmailMessage:
    headers = _headers_from_gmail(item)
    sender_name, sender_email = parseaddr(headers.get("from", ""))

    return GmailMessage(
        id=item.get("id", ""),
        thread_id=item.get("threadId", ""),
        subject=headers.get("subject") or "(no subject)",
        sender_name=sender_name or sender_email or "Unknown",
        sender_email=sender_email,
        received_at=headers.get("date") or _received_at_from_internal_date(item),
        snippet=item.get("snippet", ""),
        label_ids=tuple(item.get("labelIds") or ()),
        headers=headers,
    )


def _headers_from_gmail(item: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    payload = item.get("payload") or {}
    for header in payload.get("headers") or ():
        if not isinstance(header, dict):
            continue
        name = str(header.get("name") or "").strip().lower()
        value = str(header.get("value") or "").strip()
        if name and value:
            headers[name] = value
    return headers


def _received_at_from_internal_date(item: dict[str, Any]) -> str:
    raw_internal_date = item.get("internalDate")
    if not raw_internal_date:
        return ""

    try:
        timestamp = int(raw_internal_date) / 1000
    except (TypeError, ValueError):
        return ""

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
