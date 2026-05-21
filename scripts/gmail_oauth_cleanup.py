from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gmail_subscription_cleanup.config import load_settings
from gmail_subscription_cleanup.gmail_auth import GmailAuthenticator
from gmail_subscription_cleanup.inbox_reader import GmailInboxReader
from gmail_subscription_cleanup.report_generator import generate_cleanup_report
from gmail_subscription_cleanup.subscription_analyzer import (
    CATEGORIES,
    UNSUBSCRIBE,
    analyze_subscription_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authenticate with Gmail and generate a read-only cleanup report."
    )
    parser.add_argument("--messages", type=int, default=100, help="Inbox messages to scan.")
    parser.add_argument("--query", help="Optional Gmail search query.")
    parser.add_argument("--output", type=Path, help="Optional markdown report path.")
    args = parser.parse_args()

    settings = load_settings(ROOT / ".env")
    service = GmailAuthenticator(settings).build_service()
    inbox_reader = GmailInboxReader(service, settings.user_id)

    print("Authenticated successfully with Gmail API.")
    print(f"Using OAuth token file: {settings.token_path}")
    print(f"Using read-only scope: {settings.scopes[0]}")

    query = args.query if args.query is not None else settings.default_query
    messages = inbox_reader.list_messages(max_results=args.messages, query=query)

    print(f"\nRead {len(messages)} recent inbox message(s).")
    for message in messages[:10]:
        sender = message.sender_name or message.sender_email or "Unknown"
        print(f"- {message.received_at or 'unknown date'} | {sender} | {message.subject}")

    candidates = analyze_subscription_candidates(messages)
    print("\nNewsletter/subscription candidates:")
    for category in CATEGORIES:
        print(f"\n{category}:")
        if not candidates[category]:
            print("- None found.")
            continue
        for candidate in candidates[category]:
            metadata = candidate.unsubscribe_metadata
            unsubscribe_note = "unsubscribe metadata found" if metadata.present else "no unsubscribe metadata"
            print(
                "- "
                f"{candidate.sender_name} <{candidate.sender_email}> "
                f"({candidate.message_count} messages, {unsubscribe_note})"
            )

    if candidates[UNSUBSCRIBE]:
        print("\nIdentified unsubscribe candidates with metadata:")
        for candidate in candidates[UNSUBSCRIBE]:
            metadata = candidate.unsubscribe_metadata
            targets = metadata.mailto_links + metadata.web_links + metadata.other_targets
            target_text = ", ".join(targets) if targets else metadata.raw_header
            print(f"- {candidate.sender_email}: {target_text}")
    else:
        print("\nNo unsubscribe candidates with metadata were identified.")

    report = generate_cleanup_report(messages)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\nWrote markdown cleanup report to {args.output}.")
    else:
        print("\nMarkdown cleanup report:")
        print(report)


if __name__ == "__main__":
    main()
