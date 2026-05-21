from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from .inbox_reader import GmailMessage


UNSUBSCRIBE = "Unsubscribe"
KEEP_ORGANIZE = "Keep but organize"
HUMAN_REVIEW = "Needs human review"
CATEGORIES = (UNSUBSCRIBE, KEEP_ORGANIZE, HUMAN_REVIEW)

NEWSLETTER_TERMS = (
    "newsletter",
    "digest",
    "roundup",
    "weekly",
    "monthly",
    "webinar",
    "event",
    "community",
    "blog",
    "update",
    "insights",
)
MARKETING_TERMS = (
    "sale",
    "deal",
    "discount",
    "promo",
    "promotion",
    "offer",
    "save",
    "coupon",
    "trial",
    "upgrade",
    "sponsored",
    "recommended",
)
OPERATIONAL_TERMS = (
    "2fa",
    "account",
    "action required",
    "alert",
    "backup",
    "bill",
    "billing",
    "case",
    "code",
    "contract",
    "delivery",
    "document",
    "failed",
    "incident",
    "invoice",
    "legal",
    "login",
    "mfa",
    "order",
    "password",
    "payment",
    "payroll",
    "receipt",
    "renewal",
    "security",
    "shipment",
    "shipping",
    "signature",
    "statement",
    "support",
    "tax",
    "ticket",
    "verification",
)
HEADER_SUBSCRIPTION_SIGNALS = (
    "list-id",
    "list-help",
    "list-owner",
    "list-post",
    "list-subscribe",
    "list-unsubscribe",
)


@dataclass(frozen=True)
class UnsubscribeMetadata:
    raw_header: str = ""
    list_unsubscribe_post: str = ""
    mailto_links: tuple[str, ...] = ()
    web_links: tuple[str, ...] = ()
    other_targets: tuple[str, ...] = ()

    @property
    def present(self) -> bool:
        return bool(
            self.raw_header
            or self.list_unsubscribe_post
            or self.mailto_links
            or self.web_links
            or self.other_targets
        )

    @property
    def supports_one_click(self) -> bool:
        return "one-click" in self.list_unsubscribe_post.lower()


@dataclass(frozen=True)
class CleanupCandidate:
    category: str
    sender_name: str
    sender_email: str
    sender_domain: str
    message_count: int
    latest_received: str
    sample_subjects: tuple[str, ...]
    unsubscribe_metadata: UnsubscribeMetadata
    evidence: tuple[str, ...]
    caution: tuple[str, ...]
    recommendation: str


def analyze_subscription_candidates(
    messages: list[GmailMessage],
    min_recurring_count: int = 2,
) -> dict[str, list[CleanupCandidate]]:
    grouped = _group_by_sender(messages)
    results: dict[str, list[CleanupCandidate]] = {category: [] for category in CATEGORIES}

    for sender_key, sender_messages in grouped.items():
        candidate = _analyze_sender(sender_key, sender_messages, min_recurring_count)
        if candidate:
            results[candidate.category].append(candidate)

    for category in results:
        results[category].sort(
            key=lambda item: (item.message_count, item.latest_received),
            reverse=True,
        )
    return results


def generate_cleanup_report(
    messages: list[GmailMessage],
    report_date: date | None = None,
    min_recurring_count: int = 2,
) -> str:
    target_date = report_date or date.today()
    candidates = analyze_subscription_candidates(
        messages,
        min_recurring_count=min_recurring_count,
    )

    lines = [
        f"# Gmail Subscription Cleanup Report - {target_date.isoformat()}",
        "",
        f"Analyzed {len(messages)} recent inbox message(s).",
        "No mailbox changes were made.",
    ]

    for category in CATEGORIES:
        lines.extend(["", f"## {category}"])
        category_candidates = candidates[category]
        if not category_candidates:
            lines.append("No candidates found.")
            continue
        for candidate in category_candidates:
            lines.extend(_candidate_lines(candidate))

    lines.append("")
    return "\n".join(lines)


def parse_unsubscribe_metadata(headers: dict[str, str]) -> UnsubscribeMetadata:
    normalized = {name.lower(): value for name, value in headers.items()}
    raw_header = normalized.get("list-unsubscribe", "")
    list_unsubscribe_post = normalized.get("list-unsubscribe-post", "")
    targets = _unsubscribe_targets(raw_header)
    mailto_links = []
    web_links = []
    other_targets = []

    for target in targets:
        scheme = urlparse(target).scheme.lower()
        if scheme == "mailto":
            mailto_links.append(target)
        elif scheme in {"http", "https"}:
            web_links.append(target)
        else:
            other_targets.append(target)

    return UnsubscribeMetadata(
        raw_header=raw_header,
        list_unsubscribe_post=list_unsubscribe_post,
        mailto_links=tuple(mailto_links),
        web_links=tuple(web_links),
        other_targets=tuple(other_targets),
    )


def _analyze_sender(
    sender_key: str,
    messages: list[GmailMessage],
    min_recurring_count: int,
) -> CleanupCandidate | None:
    sender_messages = sorted(messages, key=lambda message: message.received_at, reverse=True)
    first_message = sender_messages[0]
    metadata = _first_unsubscribe_metadata(sender_messages)
    evidence = _evidence(sender_messages, metadata, min_recurring_count)
    caution = _caution(sender_messages)
    newsletter_score = _term_count(sender_messages, NEWSLETTER_TERMS)
    marketing_score = _term_count(sender_messages, MARKETING_TERMS)
    recurring = len(sender_messages) >= min_recurring_count
    subscription_like = bool(evidence)

    if not (recurring or subscription_like or metadata.present):
        return None

    if caution:
        category = HUMAN_REVIEW
        recommendation = (
            "Review manually before cleanup because the messages include "
            "transactional or operational signals."
        )
    elif metadata.present and (marketing_score or newsletter_score or recurring):
        category = UNSUBSCRIBE
        recommendation = (
            "Unsubscribe is a candidate because unsubscribe metadata is present "
            "and the sender looks recurring or subscription-oriented."
        )
    elif recurring or subscription_like:
        category = KEEP_ORGANIZE
        recommendation = (
            "Keep the sender, but consider organizing it with a newsletter or "
            "subscription label."
        )
    else:
        return None

    sender_name = first_message.sender_name or sender_key
    sender_email = first_message.sender_email or sender_key

    return CleanupCandidate(
        category=category,
        sender_name=sender_name,
        sender_email=sender_email,
        sender_domain=_domain_for(sender_email),
        message_count=len(sender_messages),
        latest_received=first_message.received_at,
        sample_subjects=_sample_subjects(sender_messages),
        unsubscribe_metadata=metadata,
        evidence=tuple(evidence),
        caution=tuple(caution),
        recommendation=recommendation,
    )


def _group_by_sender(messages: list[GmailMessage]) -> dict[str, list[GmailMessage]]:
    grouped: dict[str, list[GmailMessage]] = defaultdict(list)
    for message in messages:
        key = (message.sender_email or message.sender_name or "unknown").lower()
        grouped[key].append(message)
    return dict(grouped)


def _first_unsubscribe_metadata(messages: list[GmailMessage]) -> UnsubscribeMetadata:
    for message in messages:
        metadata = parse_unsubscribe_metadata(message.headers)
        if metadata.present:
            return metadata
    return UnsubscribeMetadata()


def _evidence(
    messages: list[GmailMessage],
    metadata: UnsubscribeMetadata,
    min_recurring_count: int,
) -> list[str]:
    evidence: list[str] = []
    if len(messages) >= min_recurring_count:
        evidence.append(f"{len(messages)} recent messages from the same sender")
    if metadata.present:
        evidence.append("List-Unsubscribe metadata is present")
    if metadata.supports_one_click:
        evidence.append("List-Unsubscribe-Post supports one-click unsubscribe")
    if _has_header_signal(messages):
        evidence.append("mailing-list headers are present")
    if _term_count(messages, NEWSLETTER_TERMS):
        evidence.append("newsletter or digest language appears in recent messages")
    if _term_count(messages, MARKETING_TERMS):
        evidence.append("marketing or promotion language appears in recent messages")
    return evidence


def _caution(messages: list[GmailMessage]) -> list[str]:
    reasons = []
    operational_matches = _matching_terms(messages, OPERATIONAL_TERMS)
    if operational_matches:
        joined = ", ".join(operational_matches[:5])
        reasons.append(f"transactional or operational language detected: {joined}")
    return reasons


def _has_header_signal(messages: list[GmailMessage]) -> bool:
    for message in messages:
        headers = message.headers
        if any(header in headers for header in HEADER_SUBSCRIPTION_SIGNALS):
            return True
        if headers.get("precedence", "").lower() in {"bulk", "list"}:
            return True
    return False


def _term_count(messages: list[GmailMessage], terms: tuple[str, ...]) -> int:
    return len(_matching_terms(messages, terms))


def _matching_terms(
    messages: list[GmailMessage],
    terms: tuple[str, ...],
) -> list[str]:
    text = " ".join(
        f"{message.subject} {message.snippet} {message.sender_name}"
        for message in messages
    ).lower()
    matches = []
    for term in terms:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, text):
            matches.append(term)
    return matches


def _unsubscribe_targets(raw_header: str) -> tuple[str, ...]:
    if not raw_header:
        return ()

    bracketed = tuple(target.strip() for target in re.findall(r"<([^>]+)>", raw_header))
    if bracketed:
        return bracketed

    return tuple(part.strip() for part in raw_header.split(",") if part.strip())


def _sample_subjects(messages: list[GmailMessage]) -> tuple[str, ...]:
    subjects = []
    seen = set()
    for message in messages:
        subject = message.subject or "(no subject)"
        if subject in seen:
            continue
        seen.add(subject)
        subjects.append(subject)
        if len(subjects) == 5:
            break
    return tuple(subjects)


def _candidate_lines(candidate: CleanupCandidate) -> list[str]:
    lines = [
        f"### {candidate.sender_name} <{candidate.sender_email}>",
        f"- Messages: {candidate.message_count}",
        f"- Latest: {candidate.latest_received or 'unknown'}",
        f"- Recommendation: {candidate.recommendation}",
        f"- Evidence: {'; '.join(candidate.evidence) if candidate.evidence else 'none'}",
        f"- Unsubscribe metadata: {_metadata_summary(candidate.unsubscribe_metadata)}",
    ]
    if candidate.caution:
        lines.append(f"- Caution: {'; '.join(candidate.caution)}")
    if candidate.sample_subjects:
        lines.append("- Sample subjects:")
        lines.extend(f"- {subject}" for subject in candidate.sample_subjects)
    return lines


def _metadata_summary(metadata: UnsubscribeMetadata) -> str:
    if not metadata.present:
        return "not found"

    parts = []
    if metadata.mailto_links:
        parts.append(f"{len(metadata.mailto_links)} mailto target(s)")
    if metadata.web_links:
        parts.append(f"{len(metadata.web_links)} web target(s)")
    if metadata.other_targets:
        parts.append(f"{len(metadata.other_targets)} other target(s)")
    if metadata.supports_one_click:
        parts.append("one-click header present")
    return ", ".join(parts) or "header present"


def _domain_for(sender_email: str) -> str:
    if "@" not in sender_email:
        return "unknown"
    return sender_email.rsplit("@", 1)[-1].lower()
