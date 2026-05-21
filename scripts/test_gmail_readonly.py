from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gmail_subscription_cleanup.config import load_settings
from gmail_subscription_cleanup.gmail_auth import GmailAuthenticator
from gmail_subscription_cleanup.inbox_reader import GmailInboxReader
from gmail_subscription_cleanup.report_generator import generate_cleanup_report


def main() -> None:
    settings = load_settings(ROOT / ".env")
    service = GmailAuthenticator(settings).build_service()
    inbox_reader = GmailInboxReader(service, settings.user_id)

    print("Authenticated successfully with Gmail API.")

    print("\nLatest inbox emails:")
    messages = inbox_reader.list_messages(max_results=10, query=settings.default_query)
    if not messages:
        print("- No inbox emails found.")
    for message in messages:
        sender = message.sender_name or message.sender_email or "Unknown"
        print(f"- {message.received_at} | {sender} | {message.subject}")

    print("\nCleanup report preview:")
    cleanup_messages = inbox_reader.list_messages(
        max_results=100,
        query=settings.default_query,
    )
    print(generate_cleanup_report(cleanup_messages))


if __name__ == "__main__":
    main()
