from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol


class PagedGraphClient(Protocol):
    def paged_get(self, path_or_url: str, params: dict[str, Any]) -> Any:
        ...


@dataclass(frozen=True)
class OutlookMessage:
    id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: str
    preview: str
    web_link: str
    is_read: bool
    conversation_id: str
    importance: str
    categories: tuple[str, ...]

    @property
    def customer_key(self) -> str:
        domain = self.sender_email.split("@")[-1].lower()
        return domain or "unknown"


class InboxReader:
    def __init__(self, graph_client: PagedGraphClient) -> None:
        self.graph_client = graph_client

    def list_messages(self, top: int = 50) -> list[OutlookMessage]:
        if top < 1:
            return []

        params = {
            "$top": min(top, 100),
            "$select": (
                "id,subject,from,sender,receivedDateTime,bodyPreview,webLink,"
                "isRead,conversationId,importance,categories"
            ),
            "$orderby": "receivedDateTime desc",
        }

        messages: list[OutlookMessage] = []
        for item in self.graph_client.paged_get("/me/mailFolders/inbox/messages", params=params):
            messages.append(message_from_graph(item))
            if len(messages) >= top:
                break

        return messages

    def group_by_customer(
        self,
        messages: list[OutlookMessage],
    ) -> dict[str, list[OutlookMessage]]:
        grouped: dict[str, list[OutlookMessage]] = defaultdict(list)
        for message in messages:
            grouped[message.customer_key].append(message)
        return dict(sorted(grouped.items()))


def message_from_graph(item: dict[str, Any]) -> OutlookMessage:
    sender = item.get("from") or item.get("sender") or {}
    email_address = sender.get("emailAddress") or {}

    return OutlookMessage(
        id=item.get("id", ""),
        subject=item.get("subject") or "(no subject)",
        sender_name=email_address.get("name") or email_address.get("address") or "Unknown",
        sender_email=email_address.get("address") or "",
        received_at=item.get("receivedDateTime") or "",
        preview=item.get("bodyPreview") or "",
        web_link=item.get("webLink") or "",
        is_read=bool(item.get("isRead", False)),
        conversation_id=item.get("conversationId") or "",
        importance=item.get("importance") or "normal",
        categories=tuple(item.get("categories") or ()),
    )
