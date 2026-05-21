from __future__ import annotations

from collections import defaultdict
from datetime import date

from .calendar_reader import OutlookEvent
from .inbox_reader import OutlookMessage


ACTION_TERMS = (
    "action",
    "approve",
    "can you",
    "could you",
    "follow up",
    "need",
    "please",
    "review",
    "todo",
)
BLOCKER_TERMS = (
    "blocked",
    "blocker",
    "dependency",
    "issue",
    "stuck",
    "waiting on",
)


def generate_daily_report(
    messages: list[OutlookMessage],
    events: list[OutlookEvent],
    report_date: date | None = None,
) -> str:
    target_date = report_date or date.today()
    lines = [
        f"# Outlook Daily Digest - {target_date.isoformat()}",
        "",
        "## Calendar",
    ]
    lines.extend(_calendar_lines(events))
    lines.extend(["", "## Inbox by Customer"])
    lines.extend(_customer_lines(messages))
    lines.extend(["", "## Action Items"])
    lines.extend(_message_lines(_action_items(messages), "No likely action items found."))
    lines.extend(["", "## Blockers and Unanswered Threads"])
    blockers = _blockers(messages)
    unanswered = _unanswered_threads(messages)
    lines.extend(_message_lines(blockers + unanswered, "No likely blockers or unanswered threads found."))
    lines.extend(["", "## Meeting Prep Notes"])
    lines.extend(_meeting_prep_lines(events, messages))
    lines.append("")
    return "\n".join(lines)


def _calendar_lines(events: list[OutlookEvent]) -> list[str]:
    active_events = [event for event in events if not event.is_cancelled]
    if not active_events:
        return ["No meetings found."]

    lines = []
    for event in active_events:
        when = _time_range(event.start, event.end)
        location = f" at {event.location}" if event.location else ""
        lines.append(f"- {when}: {event.subject}{location}")
    return lines


def _customer_lines(messages: list[OutlookMessage]) -> list[str]:
    if not messages:
        return ["No inbox messages found."]

    grouped: dict[str, list[OutlookMessage]] = defaultdict(list)
    for message in messages:
        grouped[message.customer_key].append(message)

    lines: list[str] = []
    for customer, customer_messages in sorted(grouped.items()):
        unread = sum(1 for message in customer_messages if not message.is_read)
        lines.append(f"### {customer}")
        lines.append(f"- {len(customer_messages)} message(s), {unread} unread")
        for message in customer_messages[:5]:
            lines.append(f"- {_message_summary(message)}")
    return lines


def _action_items(messages: list[OutlookMessage]) -> list[OutlookMessage]:
    return [message for message in messages if _contains_any(message, ACTION_TERMS)]


def _blockers(messages: list[OutlookMessage]) -> list[OutlookMessage]:
    return [message for message in messages if _contains_any(message, BLOCKER_TERMS)]


def _unanswered_threads(messages: list[OutlookMessage]) -> list[OutlookMessage]:
    return [
        message
        for message in messages
        if not message.is_read or "?" in f"{message.subject} {message.preview}"
    ]


def _message_lines(messages: list[OutlookMessage], empty_text: str) -> list[str]:
    if not messages:
        return [empty_text]

    seen: set[str] = set()
    lines: list[str] = []
    for message in messages:
        key = message.id or f"{message.subject}:{message.received_at}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {_message_summary(message)}")
    return lines


def _meeting_prep_lines(
    events: list[OutlookEvent],
    messages: list[OutlookMessage],
) -> list[str]:
    active_events = [event for event in events if not event.is_cancelled]
    if not active_events:
        return ["No meetings to prep."]

    lines: list[str] = []
    for event in active_events:
        related = _related_messages(event, messages)
        attendee_text = ", ".join(event.attendees[:6]) if event.attendees else event.organizer_name
        lines.append(f"### {event.subject}")
        lines.append(f"- When: {_time_range(event.start, event.end)}")
        lines.append(f"- People: {attendee_text}")
        if related:
            lines.append("- Related inbox context:")
            for message in related[:3]:
                lines.append(f"- {_message_summary(message)}")
        else:
            lines.append("- Related inbox context: none found")
    return lines


def _related_messages(
    event: OutlookEvent,
    messages: list[OutlookMessage],
) -> list[OutlookMessage]:
    event_words = _keywords(event.subject)
    if not event_words:
        return []

    related = []
    for message in messages:
        message_words = _keywords(f"{message.subject} {message.preview}")
        if event_words & message_words:
            related.append(message)
    return related


def _contains_any(message: OutlookMessage, terms: tuple[str, ...]) -> bool:
    text = f"{message.subject} {message.preview}".lower()
    return any(term in text for term in terms)


def _keywords(text: str) -> set[str]:
    ignored = {"and", "for", "meeting", "sync", "the", "with", "your"}
    words = {
        word.strip(".,:;!?()[]{}").lower()
        for word in text.split()
        if len(word.strip(".,:;!?()[]{}")) > 3
    }
    return words - ignored


def _message_summary(message: OutlookMessage) -> str:
    sender = message.sender_name or message.sender_email or "Unknown"
    preview = f" - {message.preview[:140]}" if message.preview else ""
    link = f" ([open]({message.web_link}))" if message.web_link else ""
    return f"{message.subject} from {sender}{preview}{link}"


def _time_range(start: str, end: str) -> str:
    if not start and not end:
        return "Time not specified"
    if not end:
        return start
    return f"{start} to {end}"
