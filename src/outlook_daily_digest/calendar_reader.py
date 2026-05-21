from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol


class PagedGraphClient(Protocol):
    def paged_get(
        self,
        path_or_url: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        ...


@dataclass(frozen=True)
class OutlookEvent:
    id: str
    subject: str
    organizer_name: str
    organizer_email: str
    start: str
    end: str
    location: str
    attendees: tuple[str, ...]
    web_link: str
    is_cancelled: bool


class CalendarReader:
    def __init__(self, graph_client: PagedGraphClient, outlook_timezone: str = "UTC") -> None:
        self.graph_client = graph_client
        self.outlook_timezone = outlook_timezone

    def list_events(self, start: datetime, end: datetime) -> list[OutlookEvent]:
        params = {
            "startDateTime": start.isoformat(),
            "endDateTime": end.isoformat(),
            "$select": (
                "id,subject,organizer,start,end,location,attendees,webLink,isCancelled"
            ),
            "$orderby": "start/dateTime",
        }
        headers = {"Prefer": f'outlook.timezone="{self.outlook_timezone}"'}

        return [
            event_from_graph(item)
            for item in self.graph_client.paged_get(
                "/me/calendarView",
                params=params,
                headers=headers,
            )
        ]

    def list_events_for_day(self, target_date: date) -> list[OutlookEvent]:
        start = datetime.combine(target_date, time.min)
        end = start + timedelta(days=1)
        return self.list_events(start, end)


def event_from_graph(item: dict[str, Any]) -> OutlookEvent:
    organizer = item.get("organizer") or {}
    organizer_email = organizer.get("emailAddress") or {}
    location = item.get("location") or {}

    attendees = []
    for attendee in item.get("attendees") or []:
        email_address = attendee.get("emailAddress") or {}
        name = email_address.get("name") or email_address.get("address")
        if name:
            attendees.append(name)

    return OutlookEvent(
        id=item.get("id", ""),
        subject=item.get("subject") or "(no subject)",
        organizer_name=organizer_email.get("name") or organizer_email.get("address") or "Unknown",
        organizer_email=organizer_email.get("address") or "",
        start=(item.get("start") or {}).get("dateTime") or "",
        end=(item.get("end") or {}).get("dateTime") or "",
        location=location.get("displayName") or "",
        attendees=tuple(attendees),
        web_link=item.get("webLink") or "",
        is_cancelled=bool(item.get("isCancelled", False)),
    )
